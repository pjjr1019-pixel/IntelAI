"""
aggregator.py — Converts NormalizedEvents into SignalTimeSeries rows.

This is the bridge between ingestion and detection.  It reads
NormalizedEvent rows from the database, groups them by
(entity_value, source_id, time_bucket), and writes aggregated
SignalTimeSeries rows.

It also retrieves historical series data to feed the detectors.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import numpy as np
from sqlalchemy import func, select, literal_column, case
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.config import settings
from vanguard_signal.schema.enums import TimeBucket
from vanguard_signal.schema.models.ingestion import NormalizedEvent, SourceRegistry
from vanguard_signal.schema.models.signal import SignalTimeSeries

logger = logging.getLogger(__name__)

# ── Bucket size → timedelta ──────────────────────────────────────────────
_BUCKET_DELTA: dict[TimeBucket, timedelta] = {
    TimeBucket.HOUR: timedelta(hours=1),
    TimeBucket.DAY: timedelta(days=1),
    TimeBucket.WEEK: timedelta(weeks=1),
    TimeBucket.MONTH: timedelta(days=30),
}

# How far back to look when building a series for detection
_LOOKBACK: dict[TimeBucket, int] = {
    TimeBucket.HOUR: 168,   # 7 days of hours
    TimeBucket.DAY: 90,     # 90 days
    TimeBucket.WEEK: 52,    # 1 year
    TimeBucket.MONTH: 24,   # 2 years
}


class TimeSeriesAggregator:
    """
    Aggregates NormalizedEvents into time-bucketed series and retrieves
    historical data for anomaly detection.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Aggregation ──────────────────────────────────────────────────────

    async def aggregate_events(
        self,
        bucket_size: TimeBucket = TimeBucket.DAY,
        since: datetime | None = None,
    ) -> int:
        """
        Read recent NormalizedEvents and upsert SignalTimeSeries rows.

        Returns the number of series rows created/updated.
        """
        if since is None:
            delta = _BUCKET_DELTA[bucket_size]
            since = datetime.now(timezone.utc) - (delta * 2)

        # Group by entity_value, source_id, and time bucket
        # Use SQLite-compatible bucketing when on SQLite, else Postgres date_trunc
        if settings.db.is_sqlite:
            _sqlite_fmt = {
                TimeBucket.HOUR: '%Y-%m-%d %H:00:00',
                TimeBucket.DAY: '%Y-%m-%d 00:00:00',
                TimeBucket.WEEK: '%Y-%W',
                TimeBucket.MONTH: '%Y-%m-01 00:00:00',
            }
            bucket_expr = func.strftime(
                _sqlite_fmt[bucket_size], NormalizedEvent.event_time
            )
        else:
            bucket_expr = func.date_trunc(
                bucket_size.value, NormalizedEvent.event_time
            )

        stmt = (
            select(
                NormalizedEvent.entity_value,
                NormalizedEvent.source_id,
                bucket_expr.label("bucket_start"),
                func.avg(NormalizedEvent.metric_value).label("avg_value"),
                func.count().label("sample_count"),
            )
            .where(NormalizedEvent.event_time >= since)
            .group_by(
                NormalizedEvent.entity_value,
                NormalizedEvent.source_id,
                bucket_expr,
            )
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        count = 0
        delta = _BUCKET_DELTA[bucket_size]

        for row in rows:
            entity_value = row.entity_value
            source_id = row.source_id
            bucket_start = row.bucket_start
            if bucket_start.tzinfo is None:
                bucket_start = bucket_start.replace(tzinfo=timezone.utc)
            bucket_end = bucket_start + delta

            # Upsert: check if this bucket already exists
            existing = await self._session.execute(
                select(SignalTimeSeries).where(
                    SignalTimeSeries.entity_value == entity_value,
                    SignalTimeSeries.source_id == source_id,
                    SignalTimeSeries.bucket_size == bucket_size,
                    SignalTimeSeries.bucket_start == bucket_start,
                )
            )
            existing_row = existing.scalar_one_or_none()

            if existing_row:
                existing_row.value = float(row.avg_value)
                existing_row.sample_count = int(row.sample_count)
            else:
                new_row = SignalTimeSeries(
                    entity_value=entity_value,
                    source_id=source_id,
                    bucket_size=bucket_size,
                    bucket_start=bucket_start,
                    bucket_end=bucket_end,
                    value=float(row.avg_value),
                    sample_count=int(row.sample_count),
                    coverage_score=1.0,
                )
                self._session.add(new_row)
            count += 1

        await self._session.flush()
        logger.info("Aggregated %d time-series buckets (size=%s)", count, bucket_size.value)
        return count

    # ── Retrieval for Detection ──────────────────────────────────────────

    async def get_series_values(
        self,
        entity_value: str,
        source_id: UUID,
        bucket_size: TimeBucket = TimeBucket.DAY,
        lookback: int | None = None,
    ) -> tuple[np.ndarray, list[SignalTimeSeries]]:
        """
        Retrieve historical time-series values for a single entity+source.

        Returns:
            (values_array, orm_rows) — values ordered oldest → newest
        """
        n = lookback or _LOOKBACK[bucket_size]
        cutoff = datetime.now(timezone.utc) - (_BUCKET_DELTA[bucket_size] * n)

        stmt = (
            select(SignalTimeSeries)
            .where(
                SignalTimeSeries.entity_value == entity_value,
                SignalTimeSeries.source_id == source_id,
                SignalTimeSeries.bucket_size == bucket_size,
                SignalTimeSeries.bucket_start >= cutoff,
            )
            .order_by(SignalTimeSeries.bucket_start.asc())
        )

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        if not rows:
            return np.array([]), []

        values = np.array([r.value for r in rows], dtype=np.float64)
        return values, rows

    async def get_all_active_entities(
        self,
        bucket_size: TimeBucket = TimeBucket.DAY,
        min_buckets: int = 7,
    ) -> list[tuple[str, UUID]]:
        """
        Return all (entity_value, source_id) pairs that have enough
        data points for meaningful anomaly detection.
        """
        cutoff = datetime.now(timezone.utc) - (
            _BUCKET_DELTA[bucket_size] * min_buckets
        )

        stmt = (
            select(
                SignalTimeSeries.entity_value,
                SignalTimeSeries.source_id,
            )
            .where(
                SignalTimeSeries.bucket_size == bucket_size,
                SignalTimeSeries.bucket_start >= cutoff,
            )
            .group_by(
                SignalTimeSeries.entity_value,
                SignalTimeSeries.source_id,
            )
            .having(func.count() >= min_buckets)
        )

        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
