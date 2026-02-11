"""
trending.py — Trending keywords with velocity/acceleration metrics.

Endpoints:
  GET /api/trending — Returns all active entities ranked by trend level,
                      velocity (first derivative), and a combined score.
                      Supports sorting by: level, velocity, acceleration, combined.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db, get_user_id
from vanguard_signal.api.cache import cached
from vanguard_signal.detection.aggregator import TimeSeriesAggregator
from vanguard_signal.schema.enums import TimeBucket

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/trending",
    tags=["trending"],
)


# ── Response Models ──────────────────────────────────────────────────────

class TrendingEntity(BaseModel):
    """One entity with its trend-level, velocity, and acceleration metrics."""
    entity: str
    source_id: str
    current_value: float = Field(description="Latest time-bucket value")
    previous_value: float | None = Field(description="Previous time-bucket value")
    pct_change: float = Field(description="Percent change vs previous bucket")
    velocity: float = Field(description="First derivative (rate of change)")
    acceleration: float = Field(description="Second derivative (change in velocity)")
    velocity_zscore: float = Field(description="Z-score of latest velocity vs recent history")
    acceleration_zscore: float = Field(description="Z-score of latest acceleration vs recent history")
    combined_score: float = Field(description="Weighted combination: 0.4*level_z + 0.3*vel_z + 0.3*accel_z")
    data_points: int = Field(description="Number of historical data points available")
    sparkline: list[float] = Field(description="Last N values for mini-chart")
    direction: str = Field(description="up / down / flat / accelerating_up / decelerating")


class TrendingResponse(BaseModel):
    entities: list[TrendingEntity]
    total: int
    sort_by: str
    bucket_size: str
    generated_at: str


class HistoricalTrendPoint(BaseModel):
    """A single historical data point for a trend."""
    timestamp: str = Field(description="ISO timestamp of the data point")
    value: float = Field(description="Trend value at this timestamp")
    rank: int | None = Field(description="Google Trends rank (1-100)")
    traffic: str | None = Field(description="Traffic volume description")
    velocity: float | None = Field(description="Rate of change (value difference per hour)")


class HistoricalTrendResponse(BaseModel):
    keyword: str
    geo: str
    data_points: list[HistoricalTrendPoint]
    total_points: int
    first_seen: str | None
    last_seen: str | None
    peak_rank: int | None
    avg_rank: float | None
    total_appearances: int
    generated_at: str


# ── Helpers ──────────────────────────────────────────────────────────────

def _compute_metrics(
    values: np.ndarray,
    entity_value: str,
    source_id: str,
    sparkline_len: int = 14,
) -> TrendingEntity | None:
    """Compute velocity/acceleration/combined for one entity's series."""
    if len(values) < 5:
        return None

    current = float(values[-1])
    previous = float(values[-2]) if len(values) >= 2 else None
    pct_change = ((current - previous) / abs(previous) * 100) if previous and abs(previous) > 1e-10 else 0.0

    # Derivatives
    velocity_arr = np.diff(values)
    accel_arr = np.diff(velocity_arr) if len(velocity_arr) >= 2 else np.array([0.0])

    vel_latest = float(velocity_arr[-1]) if len(velocity_arr) > 0 else 0.0
    acc_latest = float(accel_arr[-1]) if len(accel_arr) > 0 else 0.0

    # Z-scores (relative to own history)
    if len(velocity_arr) > 1:
        vel_mu = float(np.mean(velocity_arr[:-1]))
        vel_std = float(np.std(velocity_arr[:-1]))
        vel_zscore = (vel_latest - vel_mu) / vel_std if vel_std > 1e-10 else 0.0
    else:
        vel_zscore = 0.0

    if len(accel_arr) > 1:
        acc_mu = float(np.mean(accel_arr[:-1]))
        acc_std = float(np.std(accel_arr[:-1]))
        acc_zscore = (acc_latest - acc_mu) / acc_std if acc_std > 1e-10 else 0.0
    else:
        acc_zscore = 0.0

    # Level Z-score (how unusual is the current value vs history)
    val_mu = float(np.mean(values[:-1]))
    val_std = float(np.std(values[:-1]))
    level_zscore = (current - val_mu) / val_std if val_std > 1e-10 else 0.0

    # Combined score: weighted average of absolute Z-scores
    combined = 0.4 * abs(level_zscore) + 0.3 * abs(vel_zscore) + 0.3 * abs(acc_zscore)

    # Direction label
    if acc_latest > 0 and vel_latest > 0:
        direction = "accelerating_up"
    elif acc_latest < 0 and vel_latest > 0:
        direction = "decelerating_up"
    elif vel_latest > 0:
        direction = "up"
    elif vel_latest < -1e-10:
        direction = "down"
    else:
        direction = "flat"

    # Sparkline: last N values
    spark = values[-sparkline_len:].tolist()

    return TrendingEntity(
        entity=entity_value,
        source_id=str(source_id),
        current_value=round(current, 2),
        previous_value=round(previous, 2) if previous is not None else None,
        pct_change=round(pct_change, 2),
        velocity=round(vel_latest, 4),
        acceleration=round(acc_latest, 4),
        velocity_zscore=round(vel_zscore, 3),
        acceleration_zscore=round(acc_zscore, 3),
        combined_score=round(combined, 3),
        data_points=len(values),
        sparkline=[round(v, 2) for v in spark],
        direction=direction,
    )


# ── Sort key mapping ────────────────────────────────────────────────────

_SORT_KEYS: dict[str, Any] = {
    "level": lambda e: abs(e.current_value),
    "velocity": lambda e: abs(e.velocity_zscore),
    "acceleration": lambda e: abs(e.acceleration_zscore),
    "combined": lambda e: e.combined_score,
    "pct_change": lambda e: abs(e.pct_change),
}


# ── Endpoint ─────────────────────────────────────────────────────────────

@router.get("", response_model=TrendingResponse)
@cached(ttl_seconds=300, key_prefix="trending")  # Cache for 5 minutes
async def get_trending(
    sort_by: Literal["level", "velocity", "acceleration", "combined", "pct_change"] = Query(
        "combined", description="Sort field"
    ),
    bucket: Literal["hour", "day", "week"] = Query("day", description="Time granularity"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    min_points: int = Query(7, ge=3, le=90, description="Minimum data points required"),
    session: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_user_id),
) -> TrendingResponse:
    """
    Return all active entities ranked by trend level, velocity, or combined score.
    """
    from datetime import datetime, timezone

    bucket_enum = TimeBucket(bucket)
    aggregator = TimeSeriesAggregator(session)

    # Get all entities with enough history
    entities = await aggregator.get_all_active_entities(
        bucket_size=bucket_enum,
        min_buckets=min_points,
    )

    results: list[TrendingEntity] = []

    for entity_value, source_id in entities:
        values, _ = await aggregator.get_series_values(
            entity_value=entity_value,
            source_id=source_id,
            bucket_size=bucket_enum,
        )
        if len(values) < min_points:
            continue

        metric = _compute_metrics(values, entity_value, str(source_id))
        if metric:
            results.append(metric)

    # Sort
    sort_fn = _SORT_KEYS.get(sort_by, _SORT_KEYS["combined"])
    results.sort(key=sort_fn, reverse=True)
    results = results[:limit]

    return TrendingResponse(
        entities=results,
        total=len(results),
        sort_by=sort_by,
        bucket_size=bucket,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/history/{keyword}", response_model=HistoricalTrendResponse)
async def get_trend_history(
    keyword: str,
    geo: str = Query("US", description="Geographic region"),
    time_range: Literal["24h", "7d", "30d", "90d"] = Query("7d", description="Time range for historical data"),
    limit: int = Query(100, ge=1, le=1000, description="Max data points to return"),
    session: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_user_id),
) -> HistoricalTrendResponse:
    """
    Get historical trend data for a specific keyword.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, desc, and_
    from vanguard_signal.schema.models.trend import TrendKeyword, TrendTimeSeries

    # Calculate time range
    now = datetime.now(timezone.utc)
    if time_range == "24h":
        start_time = now - timedelta(hours=24)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    elif time_range == "30d":
        start_time = now - timedelta(days=30)
    elif time_range == "90d":
        start_time = now - timedelta(days=90)
    else:
        start_time = now - timedelta(days=7)  # Default to 7d

    # Get keyword info
    stmt = select(TrendKeyword).where(
        TrendKeyword.keyword == keyword,
        TrendKeyword.geo == geo
    )
    result = await session.execute(stmt)
    keyword_record = result.scalar_one_or_none()

    if not keyword_record:
        # Try fallback: look for NormalizedEvent rows in ingestion (google_trends)
        from vanguard_signal.schema.models.ingestion import NormalizedEvent, SourceRegistry
        from vanguard_signal.schema.enums import EntityType
        from sqlalchemy import and_

        stmt_fallback = (
            select(NormalizedEvent)
            .join(SourceRegistry, NormalizedEvent.source_id == SourceRegistry.id)
            .where(and_(
                NormalizedEvent.entity_type == EntityType.SEARCH_QUERY,
                NormalizedEvent.entity_value == keyword,
                SourceRegistry.name == 'google_trends',
                NormalizedEvent.event_time >= start_time,
            ))
            .order_by(NormalizedEvent.event_time.asc())
            .limit(limit)
        )
        try:
            result = await session.execute(stmt_fallback)
            events = result.scalars().all()
        except Exception:
            # If ingestion tables aren't present (dev/test sqlite), skip DB fallback
            events = []

        if events:
            raw_points = [
                {
                    'timestamp': ev.event_time.isoformat(),
                    'value': ev.metric_value,
                    'rank': None,
                    'traffic': None,
                }
                for ev in events
            ]

            # Compute velocities as in existing code
            for i in range(len(raw_points)):
                if i == 0:
                    raw_points[i]['velocity'] = None
                else:
                    prev_point = raw_points[i-1]
                    curr_point = raw_points[i]
                    from datetime import datetime as _dt
                    prev_time = _dt.fromisoformat(prev_point['timestamp'])
                    curr_time = _dt.fromisoformat(curr_point['timestamp'])
                    time_diff_hours = (curr_time - prev_time).total_seconds() / 3600
                    if time_diff_hours > 0:
                        velocity = (curr_point['value'] - prev_point['value']) / time_diff_hours
                        raw_points[i]['velocity'] = round(velocity, 4)

            return HistoricalTrendResponse(
                keyword=keyword,
                geo=geo,
                data_points=raw_points,
                total_points=len(raw_points),
                first_seen=raw_points[0]['timestamp'] if raw_points else None,
                last_seen=raw_points[-1]['timestamp'] if raw_points else None,
                peak_rank=None,
                avg_rank=None,
                total_appearances=len(raw_points),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

            # If still not found, fall through to preview via connector below

        # If we couldn't find any keyword metadata or ingestion events,
        # attempt a live Google Trends preview (no DB writes).
        from datetime import datetime as _dt

        if not keyword_record:
            from vanguard_signal.config import settings
            # If live trends are disabled by config, return a 503 to indicate not available
            if not settings.enable_live_trends:
                raise HTTPException(status_code=503, detail="Live Google Trends previews are disabled by configuration")

            from vanguard_signal.ingestion.connectors.google_trends import GoogleTrendsConnector

            connector = GoogleTrendsConnector()
            # Map time_range to a pytrends timeframe string
            timeframe_map = {
                '24h': 'now 1-d',
                '7d': 'now 7-d',
                '30d': 'now 30-d',
                '90d': 'now 90-d',
            }
            connector._geo = geo or ''
            connector._timeframe = timeframe_map.get(time_range, 'now 7-d')
            connector._delay = 1.0

            try:
                payload, elapsed = await connector.fetch_raw([keyword])
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Google Trends error: {exc}")

            interest = payload.get('interest_over_time', {})
            data_points = [
                {'timestamp': ts, 'value': list(scores.values())[0] if scores else 0, 'rank': None, 'traffic': None}
                for ts, scores in sorted(interest.items())
            ]

            # Compute velocities
            for i in range(len(data_points)):
                if i == 0:
                    data_points[i]['velocity'] = None
                else:
                    prev_point = data_points[i-1]
                    curr_point = data_points[i]
                    prev_time = _dt.fromisoformat(prev_point['timestamp'])
                    curr_time = _dt.fromisoformat(curr_point['timestamp'])
                    time_diff_hours = (curr_time - prev_time).total_seconds() / 3600
                    if time_diff_hours > 0:
                        velocity = (curr_point['value'] - prev_point['value']) / time_diff_hours
                        data_points[i]['velocity'] = round(velocity, 4)
                    else:
                        data_points[i]['velocity'] = None

            data_point_objs = [HistoricalTrendPoint(**p) for p in data_points]

            return HistoricalTrendResponse(
                keyword=keyword,
                geo=geo,
                data_points=data_point_objs,
                total_points=len(data_point_objs),
                first_seen=data_points[0]['timestamp'] if data_points else None,
                last_seen=data_points[-1]['timestamp'] if data_points else None,
                peak_rank=None,
                avg_rank=None,
                total_appearances=len(data_point_objs),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

    # Get historical time series data within time range
    stmt = (
        select(TrendTimeSeries)
        .where(
            and_(
                TrendTimeSeries.keyword_id == keyword_record.id,
                TrendTimeSeries.timestamp >= start_time
            )
        )
        .order_by(desc(TrendTimeSeries.timestamp))
        .limit(limit)
    )
    result = await session.execute(stmt)
    time_series = result.scalars().all()

    # Build response
    # First, create data points with timestamps and values
    raw_points = [
        {
            'timestamp': point.timestamp.isoformat(),
            'value': point.interest_score,
            'rank': point.rank_at_time,
            'traffic': None
        }
        for point in reversed(time_series)  # Reverse to chronological order
    ]

    # Calculate velocity for each point (rate of change per hour)
    from datetime import datetime
    for i in range(len(raw_points)):
        if i == 0:
            raw_points[i]['velocity'] = None  # No previous point
        else:
            prev_point = raw_points[i-1]
            curr_point = raw_points[i]
            prev_time = datetime.fromisoformat(prev_point['timestamp'])
            curr_time = datetime.fromisoformat(curr_point['timestamp'])
            time_diff_hours = (curr_time - prev_time).total_seconds() / 3600
            if time_diff_hours > 0:
                velocity = (curr_point['value'] - prev_point['value']) / time_diff_hours
                raw_points[i]['velocity'] = round(velocity, 4)
            else:
                raw_points[i]['velocity'] = None

    # Create HistoricalTrendPoint objects
    data_points = [
        HistoricalTrendPoint(**point)
        for point in raw_points
    ]

    return HistoricalTrendResponse(
        keyword=keyword,
        geo=geo,
        data_points=data_points,
        total_points=len(data_points),
        first_seen=keyword_record.first_seen.isoformat() if keyword_record.first_seen else None,
        last_seen=keyword_record.last_seen.isoformat() if keyword_record.last_seen else None,
        peak_rank=keyword_record.peak_rank,
        avg_rank=round(keyword_record.avg_rank, 2) if keyword_record.avg_rank else None,
        total_appearances=keyword_record.total_appearances,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
