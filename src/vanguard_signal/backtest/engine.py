"""
engine.py — Backtesting engine.

Replays historical data through the anomaly pipeline in "time-travel"
mode and evaluates detection quality against known outcomes.

Workflow:
  1. Create a BacktestRun with a time window + parameter set
  2. For each day in the window, simulate the pipeline:
       a. Pull only data available at that point in time
       b. Run detection with the specified parameters
       c. Store BacktestAlert rows
  3. Match BacktestAlerts against real alerts (if any)
  4. Score: precision, recall, F1, lead time distribution
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.detection.ensemble import EnsembleDetector
from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.enums import (
    BacktestStatus,
    Severity,
    TimeBucket,
)
from vanguard_signal.schema.models.alert import (
    Alert,
    BacktestAlert,
    BacktestRun,
    PostMortem,
)
from vanguard_signal.schema.models.signal import SignalTimeSeries

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Replays the anomaly detection pipeline on historical data.

    Parameters:
        window_start: Backtest start date.
        window_end:   Backtest end date.
        bucket_size:  Time granularity for aggregation.
        params:       Override ensemble/detector parameters.
    """

    def __init__(
        self,
        window_start: datetime,
        window_end: datetime,
        bucket_size: TimeBucket = TimeBucket.DAY,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.window_start = window_start
        self.window_end = window_end
        self.bucket_size = bucket_size
        self.params = params or {}

        # Ensemble config from params
        self._threshold = self.params.get("ensemble_threshold", 0.6)
        self._weights = {
            "weight_stl": self.params.get("weight_stl", 0.4),
            "weight_iforest": self.params.get("weight_iforest", 0.3),
            "weight_cusum": self.params.get("weight_cusum", 0.3),
        }
        self._min_series_length = self.params.get("min_series_length", 7)

    async def run(
        self,
        session: AsyncSession,
        run_name: str = "backtest",
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a full backtest run.

        Returns summary with precision, recall, F1, and per-alert details.
        """
        start_time = datetime.now(timezone.utc)

        # 1. Create BacktestRun record
        bt_run = BacktestRun(
            name=run_name,
            description=description or f"Backtest {self.window_start.date()} to {self.window_end.date()}",
            window_start=self.window_start,
            window_end=self.window_end,
            parameters=self.params,
            status=BacktestStatus.RUNNING,
            started_at=start_time,
        )
        session.add(bt_run)
        await session.flush()

        logger.info(
            "Starting backtest '%s': %s → %s",
            run_name, self.window_start.date(), self.window_end.date(),
        )

        try:
            # 2. Get all entities with data in the window
            entities = await self._get_entities_in_window(session)
            logger.info("Found %d entities with data in backtest window", len(entities))

            # 3. For each entity, simulate day-by-day detection
            bt_alerts: list[BacktestAlert] = []
            ensemble = EnsembleDetector(
                ensemble_threshold=self._threshold,
                weight_stl=self._weights["weight_stl"],
                weight_iforest=self._weights["weight_iforest"],
                weight_cusum=self._weights["weight_cusum"],
            )

            for entity_value, source_id in entities:
                alerts = await self._simulate_entity(
                    session, entity_value, source_id, ensemble, bt_run.id,
                )
                bt_alerts.extend(alerts)

            # 4. Match against real alerts
            matches = await self._match_real_alerts(session, bt_alerts, bt_run.id)

            # 5. Compute metrics
            tp = sum(1 for a in bt_alerts if a.is_true_positive is True)
            fp = sum(1 for a in bt_alerts if a.is_true_positive is False)
            # Missed: real confirmed alerts in the window without a match
            missed = await self._count_missed_events(session, bt_run.id)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + missed) if (tp + missed) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            # 6. Update BacktestRun with results
            end_time = datetime.now(timezone.utc)
            bt_run.status = BacktestStatus.COMPLETED
            bt_run.completed_at = end_time
            bt_run.duration_seconds = (end_time - start_time).total_seconds()
            bt_run.alerts_generated = len(bt_alerts)
            bt_run.true_positives = tp
            bt_run.false_positives = fp
            bt_run.missed_events = missed
            bt_run.results_summary = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "total_alerts": len(bt_alerts),
                "parameters": self.params,
            }

            await session.flush()

            summary = {
                "run_id": str(bt_run.id),
                "status": "completed",
                "alerts_generated": len(bt_alerts),
                "true_positives": tp,
                "false_positives": fp,
                "missed_events": missed,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "duration_seconds": bt_run.duration_seconds,
            }

            logger.info(
                "Backtest complete: P=%.3f R=%.3f F1=%.3f (%d alerts, %d TP, %d FP, %d missed)",
                precision, recall, f1, len(bt_alerts), tp, fp, missed,
            )

            return summary

        except Exception as exc:
            bt_run.status = BacktestStatus.FAILED
            bt_run.completed_at = datetime.now(timezone.utc)
            await session.flush()
            logger.error("Backtest failed: %s", exc, exc_info=True)
            raise

    async def _get_entities_in_window(
        self, session: AsyncSession,
    ) -> list[tuple[str, UUID]]:
        """Get entities with enough data points in the backtest window."""
        stmt = (
            select(
                SignalTimeSeries.entity_value,
                SignalTimeSeries.source_id,
            )
            .where(
                SignalTimeSeries.bucket_start >= self.window_start,
                SignalTimeSeries.bucket_end <= self.window_end,
                SignalTimeSeries.bucket_size == self.bucket_size,
            )
            .group_by(SignalTimeSeries.entity_value, SignalTimeSeries.source_id)
            .having(func.count() >= self._min_series_length)
        )
        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def _simulate_entity(
        self,
        session: AsyncSession,
        entity_value: str,
        source_id: UUID,
        ensemble: EnsembleDetector,
        run_id: UUID,
    ) -> list[BacktestAlert]:
        """Simulate detection for one entity across the backtest window."""
        # Get all series data in window
        stmt = (
            select(SignalTimeSeries)
            .where(
                SignalTimeSeries.entity_value == entity_value,
                SignalTimeSeries.source_id == source_id,
                SignalTimeSeries.bucket_start >= self.window_start,
                SignalTimeSeries.bucket_end <= self.window_end,
                SignalTimeSeries.bucket_size == self.bucket_size,
            )
            .order_by(SignalTimeSeries.bucket_start.asc())
        )
        result = await session.execute(stmt)
        series_rows = list(result.scalars().all())

        if len(series_rows) < self._min_series_length:
            return []

        values = [row.value for row in series_rows]
        alerts = []

        # Sliding window: for each point from min_length onward, run detection
        for i in range(self._min_series_length, len(values) + 1):
            window = values[:i]
            ens_result = ensemble.detect(window, entity_name=entity_value)

            if ens_result.is_anomaly:
                series_row = series_rows[i - 1]

                # Determine severity from confidence
                score = ens_result.ensemble_score
                if score >= 0.9:
                    severity = Severity.CRITICAL
                elif score >= 0.75:
                    severity = Severity.HIGH
                elif score >= 0.6:
                    severity = Severity.MEDIUM
                else:
                    severity = Severity.LOW

                bt_alert = BacktestAlert(
                    backtest_run_id=run_id,
                    primary_entity=entity_value,
                    severity=severity,
                    confidence_score=score,
                    ensemble_anomaly_score=score,
                    source_weights=self._weights,
                    reason_code=ens_result.reason_code,
                    summary_text=ens_result.summary,
                    signal_start=series_rows[0].bucket_start,
                    signal_end=series_row.bucket_end,
                )
                session.add(bt_alert)
                alerts.append(bt_alert)

        await session.flush()
        return alerts

    async def _match_real_alerts(
        self,
        session: AsyncSession,
        bt_alerts: list[BacktestAlert],
        run_id: UUID,
    ) -> int:
        """
        Match backtest alerts against real confirmed/resolved alerts.
        Updates is_true_positive and matched_real_alert_id.
        """
        matches = 0
        for bt_alert in bt_alerts:
            # Find real alerts for the same entity in a ±7-day window
            stmt = (
                select(Alert)
                .where(
                    Alert.primary_entity == bt_alert.primary_entity,
                    Alert.status.in_(["confirmed", "resolved"]),
                    Alert.signal_start <= bt_alert.signal_end + timedelta(days=7),
                    Alert.signal_end >= bt_alert.signal_start - timedelta(days=7),
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            real_alert = result.scalar_one_or_none()

            if real_alert:
                bt_alert.matched_real_alert_id = real_alert.id
                bt_alert.is_true_positive = True
                matches += 1
            else:
                bt_alert.is_true_positive = False

        await session.flush()
        return matches

    async def _count_missed_events(
        self,
        session: AsyncSession,
        run_id: UUID,
    ) -> int:
        """Count real confirmed alerts in the window that had no backtest match."""
        # All real confirmed alerts in window
        real_stmt = (
            select(func.count(Alert.id))
            .where(
                Alert.status.in_(["confirmed", "resolved"]),
                Alert.signal_start >= self.window_start,
                Alert.signal_end <= self.window_end,
            )
        )
        total_real = (await session.execute(real_stmt)).scalar() or 0

        # How many were matched
        matched_stmt = (
            select(func.count(BacktestAlert.id))
            .where(
                BacktestAlert.backtest_run_id == run_id,
                BacktestAlert.is_true_positive == True,
            )
        )
        matched = (await session.execute(matched_stmt)).scalar() or 0

        return max(0, total_real - matched)


# ═════════════════════════════════════════════════════════════════════════
# Convenience function
# ═════════════════════════════════════════════════════════════════════════

async def run_backtest(
    window_start: datetime,
    window_end: datetime,
    name: str = "backtest",
    **params: Any,
) -> dict[str, Any]:
    """One-shot: open session → run backtest → commit → return results."""
    engine = BacktestEngine(
        window_start=window_start,
        window_end=window_end,
        params=params,
    )
    async with get_session() as session:
        return await engine.run(session, run_name=name)
