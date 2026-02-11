"""
clusterer.py — Semantic clustering of entity embeddings.

Groups related search terms / entities into semantic clusters using
HDBSCAN (density-based, no need to pre-specify k).  Computes centroid
vectors and stores clusters in the SemanticCluster/Member tables.

Also computes DRIFT: how much a cluster's centroid moved since the
prior time window — the core "semantic shift" signal.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.semantic.embedder import cosine_distance, embed_texts
from vanguard_signal.schema.models.signal import SemanticCluster, SemanticClusterMember

logger = logging.getLogger(__name__)

# Minimum cluster size for HDBSCAN
_MIN_CLUSTER_SIZE = int(__import__("os").getenv("VS_MIN_CLUSTER_SIZE", "3"))
# Drift threshold: above this → flag as rapid semantic shift
_DRIFT_THRESHOLD = float(__import__("os").getenv("VS_DRIFT_THRESHOLD", "0.15"))


def _cluster_embeddings(
    embeddings: np.ndarray,
    min_cluster_size: int = _MIN_CLUSTER_SIZE,
) -> np.ndarray:
    """
    Cluster embedding vectors using HDBSCAN.

    Returns:
        labels array: -1 = noise, 0+ = cluster ID.
    """
    try:
        from hdbscan import HDBSCAN
    except ImportError:
        # Fallback to sklearn KMeans if HDBSCAN not installed
        logger.warning("hdbscan not installed, falling back to KMeans(k=5)")
        from sklearn.cluster import KMeans
        n_clusters = min(5, len(embeddings))
        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        return km.fit_predict(embeddings)

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    return clusterer.fit_predict(embeddings)


async def _get_prior_clusters(
    session: AsyncSession,
) -> dict[str, SemanticCluster]:
    """Load the most recent cluster for each label (for drift comparison)."""
    stmt = (
        select(SemanticCluster)
        .order_by(SemanticCluster.window_end.desc())
        .limit(500)
    )
    result = await session.execute(stmt)
    clusters = result.scalars().all()

    # Keep only the most recent per label
    latest: dict[str, SemanticCluster] = {}
    for c in clusters:
        if c.label and c.label not in latest:
            latest[c.label] = c
    return latest


async def run_clustering(
    entities: Sequence[str],
    session: AsyncSession,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> dict[str, Any]:
    """
    Full clustering cycle:
      1. Embed all entities
      2. Cluster with HDBSCAN
      3. Compute centroids
      4. Compare to prior clusters → drift scores
      5. Store SemanticCluster + SemanticClusterMember rows

    Returns summary dict with cluster count and max drift.
    """
    if not entities:
        return {"clusters": 0, "max_drift": 0.0}

    now = datetime.now(timezone.utc)
    window_start = window_start or now
    window_end = window_end or now

    # 1. Embed
    entity_list = list(entities)
    embeddings = embed_texts(entity_list)
    logger.info("Embedded %d entities (%d dims)", len(entity_list), embeddings.shape[1])

    # 2. Cluster
    labels = _cluster_embeddings(embeddings)
    unique_labels = set(labels)
    unique_labels.discard(-1)  # remove noise label
    logger.info("Found %d clusters (%d noise points)", len(unique_labels), (labels == -1).sum())

    # 3. Load prior clusters for drift comparison
    prior_clusters = await _get_prior_clusters(session)

    max_drift = 0.0
    clusters_created = 0

    for cluster_id in sorted(unique_labels):
        mask = labels == cluster_id
        member_indices = np.where(mask)[0]
        member_embeddings = embeddings[mask]
        member_entities = [entity_list[i] for i in member_indices]

        # Compute centroid
        centroid = member_embeddings.mean(axis=0)
        centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)

        # Auto-label: most central entity
        distances = [
            cosine_distance(member_embeddings[i], centroid_norm)
            for i in range(len(member_embeddings))
        ]
        most_central_idx = int(np.argmin(distances))
        label = member_entities[most_central_idx]

        # Drift: compare to prior cluster with same label
        drift_score = 0.0
        prior_id = None
        if label in prior_clusters:
            prior = prior_clusters[label]
            prior_centroid = np.array(prior.centroid_vector, dtype=np.float32)
            drift_score = cosine_distance(centroid_norm, prior_centroid)
            prior_id = prior.id
            max_drift = max(max_drift, drift_score)

        drift_flag = drift_score > _DRIFT_THRESHOLD

        # Store cluster
        cluster_row = SemanticCluster(
            window_start=window_start,
            window_end=window_end,
            label=label,
            centroid_vector=centroid_norm.tolist(),
            cluster_size=len(member_entities),
            drift_score=drift_score,
            drift_flag=drift_flag,
            prior_cluster_id=prior_id,
        )
        session.add(cluster_row)
        await session.flush()

        # Store members
        for i, entity in enumerate(member_entities):
            member_row = SemanticClusterMember(
                cluster_id=cluster_row.id,
                entity_value=entity,
                embedding_vector=member_embeddings[i].tolist(),
                distance_to_centroid=distances[i],
            )
            session.add(member_row)

        clusters_created += 1
        if drift_flag:
            logger.warning(
                "DRIFT DETECTED: cluster '%s' drifted %.4f (threshold %.4f)",
                label, drift_score, _DRIFT_THRESHOLD,
            )

    await session.flush()

    return {
        "clusters": clusters_created,
        "max_drift": round(max_drift, 6),
        "total_entities": len(entity_list),
        "noise_entities": int((labels == -1).sum()),
    }
