"""
pipeline.py — End-to-end anomaly detection orchestrator.

This is the "main loop" for detection.  It:

  1. Aggregates: NormalizedEvents → SignalTimeSeries (via aggregator)
  2. Detects:    For each entity with enough history, runs the ensemble
  3. Stores:     Writes AnomalyResult rows (even for non-anomalies, for audit)
  4. Alerts:     If anomaly detected → creates Alert + EvidenceChain

Designed to run after every ingestion cycle, or on its own schedule.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.config import settings
from vanguard_signal.detection.aggregator import TimeSeriesAggregator
from vanguard_signal.detection.analogs import find_historical_analogs, store_analogs
from vanguard_signal.detection.correlation_detector import CrossCorrelationDetector
from vanguard_signal.detection.ensemble import EnsembleDetector, EnsembleResult
from vanguard_signal.detection.evidence import EvidenceBuilder
from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.enums import TimeBucket
from vanguard_signal.schema.models.signal import AnomalyResult

logger = logging.getLogger(__name__)


def _get_rl_weights() -> dict[str, float]:
    """Load RL-learned weights if enabled, else return empty dict."""
    if not settings.enable_rl_feedback:
        return {}
    try:
        from vanguard_signal.detection.rl_feedback import load_priors
        priors = load_priors()
        weights = priors.mean_weights()
        logger.info(
            "RL weights loaded: STL=%.3f IF=%.3f CUSUM=%.3f VEL=%.3f",
            weights["weight_stl"], weights["weight_iforest"],
            weights["weight_cusum"], weights["weight_velocity"],
        )
        return weights
    except Exception as exc:
        logger.warning("RL weight loading failed, using defaults: %s", exc)
        return {}

# Minimum data points needed for meaningful detection
_MIN_SERIES_LENGTH = 7


class AnomalyPipeline:
    """
    Orchestrates the full aggregate → detect → store → alert cycle.

    Parameters:
        bucket_size:        Time granularity for aggregation.
        min_series_length:  Skip entities with fewer data points.
        ensemble_kwargs:    Passed directly to EnsembleDetector.__init__.
    """

    def __init__(
        self,
        bucket_size: TimeBucket = TimeBucket.DAY,
        min_series_length: int = _MIN_SERIES_LENGTH,
        **ensemble_kwargs: Any,
    ) -> None:
        self._bucket_size = bucket_size
        self._min_length = min_series_length
        # Merge RL-learned weights (if enabled) with caller overrides
        rl_weights = _get_rl_weights()
        merged = {**rl_weights, **ensemble_kwargs}
        self._ensemble = EnsembleDetector(**merged)
        self._correlation = CrossCorrelationDetector()

    async def run(self, session: AsyncSession) -> dict[str, Any]:
        """
        Execute one full detection cycle.

        Returns a summary dict with counts and details.
        """
        summary: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bucket_size": self._bucket_size.value,
            "entities_scanned": 0,
            "anomalies_detected": 0,
            "alerts_created": 0,
            "analogs_matched": 0,
            "ws_broadcasts": 0,
            "correlation_pairs_analysed": 0,
            "correlation_anomalous_pairs": 0,
            "co_movement_score": 0.0,
            "errors": 0,
        }

        aggregator = TimeSeriesAggregator(session)
        evidence_builder = EvidenceBuilder(session)

        # ── Step 1: Aggregate recent events into time series ─────────────
        logger.info("Step 1: Aggregating events into %s buckets…", self._bucket_size.value)
        buckets_written = await aggregator.aggregate_events(
            bucket_size=self._bucket_size,
        )
        logger.info("  → %d series buckets written", buckets_written)

        # ── Step 2: Get all entities with enough history ─────────────────
        entities = await aggregator.get_all_active_entities(
            bucket_size=self._bucket_size,
            min_buckets=self._min_length,
        )
        summary["entities_scanned"] = len(entities)
        logger.info("Step 2: Found %d entities with ≥%d data points", len(entities), self._min_length)

        # ── Step 2b: Run semantic clustering if enabled ───────────────
        if settings.enable_semantic_engine:
            try:
                from vanguard_signal.semantic.clusterer import run_clustering
                entity_names = [e[0] for e in entities]
                cluster_result = await run_clustering(entity_names, session)
                summary["semantic_clusters"] = cluster_result.get("clusters", 0)
                summary["max_drift"] = cluster_result.get("max_drift", 0.0)
                logger.info(
                    "  Semantic clustering: %d clusters, max_drift=%.4f",
                    cluster_result.get("clusters", 0),
                    cluster_result.get("max_drift", 0.0),
                )
            except Exception as sem_exc:
                logger.warning("Semantic clustering failed: %s", sem_exc)

        # ── Step 3: Run detection on each entity ─────────────────────────
        # Also collect series for cross-correlation analysis
        entity_series_map: dict[str, np.ndarray] = {}

        for entity_value, source_id in entities:
            try:
                # Retrieve historical series
                values, series_rows = await aggregator.get_series_values(
                    entity_value=entity_value,
                    source_id=source_id,
                    bucket_size=self._bucket_size,
                )

                if len(values) < self._min_length:
                    continue

                # Collect for cross-correlation analysis
                entity_series_map[entity_value] = values

                # Run ensemble detector
                result: EnsembleResult = self._ensemble.detect(
                    values, entity_name=entity_value
                )

                # The latest series row is what we're evaluating
                latest_series = series_rows[-1]

                # ── Step 4: Store AnomalyResult (always, for audit) ──────
                anomaly_dict = result.to_anomaly_dict()
                anomaly_row = AnomalyResult(
                    series_id=latest_series.id,
                    detection_time=datetime.now(timezone.utc),
                    **anomaly_dict,
                )
                session.add(anomaly_row)
                await session.flush()

                # ── Step 5: Create alert if anomaly detected ─────────────
                if result.is_anomaly:
                    summary["anomalies_detected"] += 1

                    alert = await evidence_builder.create_alert_with_evidence(
                        ensemble_result=result,
                        series_row=latest_series,
                        anomaly_row=anomaly_row,
                        entity_value=entity_value,
                    )
                    summary["alerts_created"] += 1

                    # Record analytics for rule-based alerts
                    try:
                        from vanguard_signal.detection.analytics import get_analytics_service
                        analytics_service = get_analytics_service()
                        await analytics_service.record_alert_creation(alert)
                    except Exception as analytics_exc:
                        logger.debug("Analytics recording failed: %s", analytics_exc)

                    # ── Step 6: Find historical analogs ───────────────────
                    try:
                        analogs = await find_historical_analogs(alert, session)
                        if analogs:
                            await store_analogs(alert, analogs, session)
                            summary["analogs_matched"] += len(analogs)
                    except Exception as analog_exc:
                        logger.warning(
                            "Analog matching failed for alert %s: %s",
                            alert.id, analog_exc,
                        )

                    # ── Step 7: Broadcast via WebSocket ───────────────────
                    # Get template-rendered content for notifications
                    template_content = None
                    try:
                        from vanguard_signal.detection.templates import AlertTemplateService
                        template_service = AlertTemplateService(session)
                        template = await template_service.get_template_for_alert(alert)
                        if template:
                            template_content = template_service.render_template(template, alert)
                    except Exception as template_exc:
                        logger.debug("Template rendering failed: %s", template_exc)

                    alert_payload = {
                        "id": str(alert.id),
                        "primary_entity": entity_value,
                        "severity": alert.severity.value,
                        "confidence_score": alert.confidence_score,
                        "reason_code": alert.reason_code,
                        "summary_text": alert.summary_text,
                        "signal_start": alert.signal_start.isoformat(),
                        "signal_end": alert.signal_end.isoformat(),
                        # Additional fields for email templates
                        "term": entity_value,
                        "anomaly_score": alert.ensemble_anomaly_score if hasattr(alert, 'ensemble_anomaly_score') else alert.confidence_score,
                        "source": source_id,
                        "detected_at": alert.created_at.isoformat(),
                        "dashboard_url": "http://localhost:3000/alerts",
                        "acknowledge_url": f"http://localhost:3000/alerts/{alert.id}/acknowledge",
                        "resolve_url": f"http://localhost:3000/alerts/{alert.id}/resolve",
                        # Template-rendered content
                        "template_content": template_content,
                    }
                    try:
                        from vanguard_signal.api.websocket import broadcast_alert
                        await broadcast_alert(alert_payload)
                        summary["ws_broadcasts"] += 1
                    except Exception as ws_exc:
                        logger.debug("WebSocket broadcast skipped: %s", ws_exc)

                    # ── Step 8: Send notifications (Slack/Email/Webhook) ──
                    try:
                        # Check if alert is silenced before sending notifications
                        from vanguard_signal.detection.silence import get_silence_service
                        silence_service = get_silence_service()
                        is_silenced, silence_reason = await silence_service.is_alert_silenced(
                            alert_id=str(alert.id),
                            entity=entity_value
                        )

                        if is_silenced:
                            logger.debug(f"Alert {alert.id} silenced: {silence_reason}")
                            summary.setdefault("alerts_silenced", 0)
                            summary["alerts_silenced"] += 1
                        else:
                            from vanguard_signal.notifications.queue import get_alert_queue
                            alert_queue = get_alert_queue()
                            queued = await alert_queue.enqueue_alert(
                                alert_id=str(alert.id),
                                alert_payload=alert_payload,
                                severity=alert.severity
                            )
                            if queued:
                                summary.setdefault("alerts_queued", 0)
                                summary["alerts_queued"] += 1
                                logger.debug("Alert %s queued for notification", alert.id)
                            else:
                                logger.warning("Alert %s could not be queued (queue full)", alert.id)
                    except Exception as notify_exc:
                        logger.debug("Notification dispatch skipped: %s", notify_exc)

            except Exception as exc:
                summary["errors"] += 1
                logger.error(
                    "Detection failed for entity='%s' source=%s: %s",
                    entity_value,
                    source_id,
                    exc,
                    exc_info=True,
                )

        # ── Step 9: Cross-keyword correlation analysis ────────────────
        try:
            if len(entity_series_map) >= 2:
                logger.info(
                    "Step 9: Running cross-correlation on %d entities…",
                    len(entity_series_map),
                )
                corr_result = self._correlation.detect(entity_series_map)
                summary["correlation_pairs_analysed"] = corr_result.pairs_analysed
                summary["correlation_anomalous_pairs"] = len(corr_result.pairs)
                summary["co_movement_score"] = corr_result.co_movement_score

                if corr_result.co_movement_score > 0.3:
                    logger.warning(
                        "⚠ CROSS-CORRELATION: score=%.3f, %d anomalous pairs | %s",
                        corr_result.co_movement_score,
                        len(corr_result.pairs),
                        corr_result.summary,
                    )
                    # Broadcast correlation alert via WebSocket
                    corr_payload = {
                        "type": "correlation_alert",
                        **corr_result.to_dict(),
                    }
                    try:
                        from vanguard_signal.api.websocket import broadcast_alert
                        await broadcast_alert(corr_payload)
                        summary["ws_broadcasts"] += 1
                    except Exception as ws_exc:
                        logger.debug("Correlation WS broadcast skipped: %s", ws_exc)
                else:
                    logger.debug(
                        "  Cross-correlation normal: score=%.3f",
                        corr_result.co_movement_score,
                    )
        except Exception as corr_exc:
            logger.warning("Cross-correlation analysis failed: %s", corr_exc)

        # ── Step 10: Check for alert escalations ───────────────────────
        try:
            from vanguard_signal.detection.escalation import run_escalation_check
            escalated_count = await run_escalation_check()
            summary["alerts_escalated"] = escalated_count
        except Exception as esc_exc:
            logger.warning("Alert escalation check failed: %s", esc_exc)
            summary["alerts_escalated"] = 0

        logger.info(
            "=== Detection cycle complete: %d scanned, %d anomalies, %d alerts, "
            "correlation=%.3f, %d escalated, %d errors ===",
            summary["entities_scanned"],
            summary["anomalies_detected"],
            summary["alerts_created"],
            summary["co_movement_score"],
            summary["alerts_escalated"],
            summary["errors"],
        )

        return summary


# ═════════════════════════════════════════════════════════════════════════
# Convenience function — run one full cycle with a fresh session
# ═════════════════════════════════════════════════════════════════════════

async def run_detection_cycle(
    bucket_size: TimeBucket = TimeBucket.DAY,
    min_series_length: int = _MIN_SERIES_LENGTH,
    **ensemble_kwargs: Any,
) -> dict[str, Any]:
    """
    One-shot: open session → aggregate → detect → alert → commit.
    """
    pipeline = AnomalyPipeline(
        bucket_size=bucket_size,
        min_series_length=min_series_length,
        **ensemble_kwargs,
    )

    async with get_session() as session:
        return await pipeline.run(session)
