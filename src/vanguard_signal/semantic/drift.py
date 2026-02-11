"""
drift.py — Semantic drift scoring utilities.

Provides functions to:
  • Compute per-entity drift (how much an entity's context changed)
  • Compute aggregate drift for an alert (used in confidence_score)
  • Query recent drift flags for the dashboard
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.models.signal import SemanticCluster, SemanticClusterMember

logger = logging.getLogger(__name__)


async def get_entity_drift_score(
    entity_value: str,
    session: AsyncSession,
    lookback_hours: int = 168,  # 7 days
) -> float:
    """
    Get the maximum drift_score for clusters containing this entity
    within the lookback window.

    Returns 0.0 if entity has no cluster membership or no drift.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    stmt = (
        select(func.max(SemanticCluster.drift_score))
        .join(
            SemanticClusterMember,
            SemanticClusterMember.cluster_id == SemanticCluster.id,
        )
        .where(
            SemanticClusterMember.entity_value == entity_value,
            SemanticCluster.window_end >= cutoff,
        )
    )
    result = await session.execute(stmt)
    score = result.scalar()
    return float(score) if score else 0.0


async def get_drifting_clusters(
    session: AsyncSession,
    lookback_hours: int = 168,
    min_drift: float = 0.1,
) -> list[dict]:
    """
    Return all clusters with significant drift in the lookback window.
    Used by the dashboard to show "Rapidly Shifting Topics."
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    stmt = (
        select(SemanticCluster)
        .where(
            SemanticCluster.drift_flag == True,
            SemanticCluster.drift_score >= min_drift,
            SemanticCluster.window_end >= cutoff,
        )
        .order_by(SemanticCluster.drift_score.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    clusters = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "label": c.label,
            "drift_score": round(c.drift_score, 4),
            "cluster_size": c.cluster_size,
            "window_start": c.window_start.isoformat(),
            "window_end": c.window_end.isoformat(),
        }
        for c in clusters
    ]


async def compute_composite_drift(
    entities: Sequence[str],
    session: AsyncSession,
) -> float:
    """
    Compute a composite drift score across multiple entities.
    Takes the weighted average of individual entity drifts.

    Used when building the confidence_score for multi-entity alerts.
    """
    if not entities:
        return 0.0

    scores = []
    for entity in entities:
        score = await get_entity_drift_score(entity, session)
        scores.append(score)

    if not scores:
        return 0.0

    # Weight: higher drifts contribute more
    total = sum(scores)
    if total == 0.0:
        return 0.0

    # Weighted average biased toward max
    avg = sum(scores) / len(scores)
    mx = max(scores)
    return 0.6 * mx + 0.4 * avg
