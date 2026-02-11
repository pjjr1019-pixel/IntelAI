"""
analogs.py — Historical Analog Matching engine.

Finds past alerts whose signal patterns most closely resemble a
current alert, using DTW (Dynamic Time Warping) + cosine similarity.

This enables analysts to see: "This pattern looks like what happened
before [2023 banking crisis / 2020 COVID spike / …]."
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID

import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.models.alert import Alert, HistoricalAnalog
from vanguard_signal.schema.models.signal import AnomalyResult, SignalTimeSeries

logger = logging.getLogger(__name__)

# How many analogs to return per alert
_TOP_K = 3
# Minimum similarity score to store
_MIN_SIMILARITY = 0.3
# How far back to search for historical patterns
_LOOKBACK_DAYS = 365


def _normalize_series(values: Sequence[float]) -> np.ndarray:
    """Z-normalize a time series for shape comparison."""
    arr = np.array(values, dtype=np.float64)
    std = arr.std()
    if std < 1e-10:
        return np.zeros_like(arr)
    return (arr - arr.mean()) / std


def _dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Dynamic Time Warping distance between two 1-D series.

    Simplified O(n*m) implementation — sufficient for alert-length
    series (typically 7-90 points). For longer series, use
    fastdtw or dtaidistance.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")

    dtw = np.full((n + 1, m + 1), np.inf)
    dtw[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(a[i - 1] - b[j - 1])
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])

    return float(dtw[n, m]) / max(n, m)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two series (padded to same length)."""
    max_len = max(len(a), len(b))
    a_pad = np.pad(a, (0, max_len - len(a)))
    b_pad = np.pad(b, (0, max_len - len(b)))

    dot = np.dot(a_pad, b_pad)
    norm = np.linalg.norm(a_pad) * np.linalg.norm(b_pad)
    if norm < 1e-10:
        return 0.0
    return float(dot / norm)


def compute_similarity(
    current_series: Sequence[float],
    historical_series: Sequence[float],
    method: str = "dtw_cosine",
) -> float:
    """
    Compute a similarity score (0.0 – 1.0) between two time series.

    Methods:
      dtw_cosine — blend of DTW inversed distance + cosine similarity
      cosine     — cosine similarity only (faster)
      dtw        — DTW inversed distance only (shape-focused)
    """
    a = _normalize_series(current_series)
    b = _normalize_series(historical_series)

    if method == "cosine":
        return max(0.0, _cosine_similarity(a, b))

    if method == "dtw":
        dtw_dist = _dtw_distance(a, b)
        return max(0.0, 1.0 - dtw_dist / 10.0)  # normalize roughly

    # Default: dtw_cosine blend
    dtw_dist = _dtw_distance(a, b)
    dtw_sim = max(0.0, 1.0 - dtw_dist / 10.0)
    cos_sim = max(0.0, _cosine_similarity(a, b))
    return 0.5 * dtw_sim + 0.5 * cos_sim


async def _get_series_for_alert(
    alert: Alert,
    session: AsyncSession,
) -> list[float]:
    """Retrieve the time-series values that generated this alert."""
    if not alert.anomaly_result_id:
        return []

    anomaly = await session.get(AnomalyResult, alert.anomaly_result_id)
    if not anomaly:
        return []

    # Get the full series for this entity
    stmt = (
        select(SignalTimeSeries.value)
        .where(
            SignalTimeSeries.entity_value == alert.primary_entity,
        )
        .order_by(SignalTimeSeries.bucket_start.asc())
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def find_historical_analogs(
    alert: Alert,
    session: AsyncSession,
    top_k: int = _TOP_K,
    min_similarity: float = _MIN_SIMILARITY,
    lookback_days: int = _LOOKBACK_DAYS,
) -> list[dict[str, Any]]:
    """
    Find the top-k most similar historical alerts by time-series shape.

    Steps:
      1. Get the current alert's series
      2. Find all resolved/confirmed alerts from the lookback window
      3. Get each historical alert's series
      4. Compute similarity scores
      5. Return top-k above threshold

    Returns list of dicts with matched_alert_id, similarity_score, method, summary.
    """
    current_series = await _get_series_for_alert(alert, session)
    if len(current_series) < 3:
        logger.debug("Alert %s has too few series points for analog matching", alert.id)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # Find historical alerts (not the current one)
    stmt = (
        select(Alert)
        .where(
            Alert.id != alert.id,
            Alert.created_at >= cutoff,
            Alert.status.in_(["confirmed", "resolved", "archived"]),
        )
        .order_by(Alert.created_at.desc())
        .limit(200)
    )
    result = await session.execute(stmt)
    historical_alerts = result.scalars().all()

    candidates: list[dict[str, Any]] = []

    for hist_alert in historical_alerts:
        hist_series = await _get_series_for_alert(hist_alert, session)
        if len(hist_series) < 3:
            continue

        sim = compute_similarity(current_series, hist_series)
        if sim >= min_similarity:
            candidates.append({
                "matched_alert": hist_alert,
                "similarity_score": round(sim, 4),
                "method": "dtw_cosine",
            })

    # Sort by similarity descending
    candidates.sort(key=lambda c: c["similarity_score"], reverse=True)

    return candidates[:top_k]


async def store_analogs(
    alert: Alert,
    analogs: list[dict[str, Any]],
    session: AsyncSession,
) -> list[HistoricalAnalog]:
    """Persist historical analog matches to the database."""
    rows = []
    for analog in analogs:
        matched = analog["matched_alert"]
        row = HistoricalAnalog(
            alert_id=alert.id,
            matched_alert_id=matched.id,
            similarity_score=analog["similarity_score"],
            similarity_method=analog["method"],
            reference_period_start=matched.signal_start,
            reference_period_end=matched.signal_end,
            analog_summary=(
                f"Pattern similar to '{matched.primary_entity}' alert from "
                f"{matched.signal_start.strftime('%Y-%m-%d')} "
                f"(confidence {matched.confidence_score:.2f}, "
                f"outcome: {matched.status.value})"
            ),
        )
        session.add(row)
        rows.append(row)

    await session.flush()
    logger.info(
        "Stored %d historical analogs for alert %s",
        len(rows), alert.id,
    )
    return rows
