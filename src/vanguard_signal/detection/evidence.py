"""
evidence.py — Auto-generates evidence chains, confidence scores, and alert summaries.

This module is the "explainability engine."  When the pipeline flags an
anomaly, this module:

  1. Computes the final CONFIDENCE SCORE by combining:
     - Ensemble anomaly score
     - Source health weights (graceful degradation)
     - Semantic drift score (0.0 in Phase 1)

  2. Traces the EVIDENCE CHAIN backwards:
     AnomalyResult → SignalTimeSeries → NormalizedEvents → RawIngestion
     Every UUID is recorded so auditors can follow the breadcrumbs.

  3. Determines SEVERITY based on confidence + domain heuristics.

  4. Generates the SUMMARY TEXT for human analysts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.config import settings
from vanguard_signal.detection.ensemble import EnsembleResult
from vanguard_signal.detection.templates import AlertTemplateService
from vanguard_signal.ingestion.health import SourceHealthMonitor
from vanguard_signal.schema.enums import AlertStatus, Severity
from vanguard_signal.schema.models.alert import Alert, EvidenceChain
from vanguard_signal.schema.models.ingestion import NormalizedEvent, SourceRegistry
from vanguard_signal.schema.models.signal import AnomalyResult, SignalTimeSeries
from vanguard_signal.schema.validators import AlertCreate, EvidenceChainCreate

logger = logging.getLogger(__name__)

# ── Severity thresholds ──────────────────────────────────────────────────
_SEVERITY_THRESHOLDS = {
    Severity.CRITICAL: 0.90,
    Severity.HIGH: 0.75,
    Severity.MEDIUM: 0.55,
    Severity.LOW: 0.0,
}


def compute_severity(confidence: float) -> Severity:
    """Map a confidence score (0–1) to a severity level."""
    for sev, threshold in _SEVERITY_THRESHOLDS.items():
        if confidence >= threshold:
            return sev
    return Severity.LOW


class EvidenceBuilder:
    """
    Builds fully traceable alerts with evidence chains from anomaly results.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_confidence_score(
        self,
        ensemble_score: float,
        source_id: UUID,
        semantic_drift: float = 0.0,
    ) -> tuple[float, dict[str, float]]:
        """
        Compute the final confidence score incorporating source health weights.

        Returns:
            (confidence_score, source_weights_dict)
        """
        # Get all active sources for weight computation
        stmt = select(SourceRegistry).where(SourceRegistry.is_active.is_(True))
        result = await self._session.execute(stmt)
        all_sources = list(result.scalars().all())

        source_weights = SourceHealthMonitor.compute_all_weights(all_sources)

        # Find this source's weight
        source = await self._session.get(SourceRegistry, source_id)
        source_name = source.name if source else "unknown"
        source_weight = source_weights.get(source_name, 1.0)

        # If semantic engine enabled, compute drift for this entity
        if settings.enable_semantic_engine and semantic_drift == 0.0:
            try:
                from vanguard_signal.semantic.drift import get_entity_drift_score
                # We need entity value — passed via the caller if available
                # For now, use what was provided
            except ImportError:
                pass

        # Confidence = ensemble_score × source_reliability + semantic_drift component
        # Clamp to [0, 1]
        confidence = min(
            1.0,
            max(0.0, ensemble_score * source_weight + semantic_drift * 0.2),
        )

        return confidence, source_weights

    async def trace_evidence(
        self,
        series_row: SignalTimeSeries,
        anomaly_row: AnomalyResult,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """
        Trace the lineage from anomaly back to raw ingestion.

        Returns:
            (raw_ids, normalized_event_ids, series_ids, anomaly_ids)
        """
        series_ids = [str(series_row.id)]
        anomaly_ids = [str(anomaly_row.id)]

        # Find NormalizedEvents that contributed to this series bucket
        stmt = (
            select(NormalizedEvent.id, NormalizedEvent.raw_id)
            .where(
                NormalizedEvent.entity_value == series_row.entity_value,
                NormalizedEvent.source_id == series_row.source_id,
                NormalizedEvent.event_time >= series_row.bucket_start,
                NormalizedEvent.event_time < series_row.bucket_end,
            )
        )
        result = await self._session.execute(stmt)
        event_rows = result.all()

        normalized_event_ids = [str(r[0]) for r in event_rows]
        raw_ids = list({str(r[1]) for r in event_rows})  # deduplicate

        return raw_ids, normalized_event_ids, series_ids, anomaly_ids

    async def create_alert_with_evidence(
        self,
        ensemble_result: EnsembleResult,
        series_row: SignalTimeSeries,
        anomaly_row: AnomalyResult,
        entity_value: str,
    ) -> Alert:
        """
        Full alert creation pipeline:
          1. Compute confidence score
          2. Determine severity
          3. Create Alert row
          4. Trace evidence chain
          5. Create EvidenceChain row
          6. Return the complete Alert

        This is the MAIN entry point called by the pipeline.
        """
        # 1. Confidence (with drift scoring if semantic engine is on)
        drift_score = 0.0
        if settings.enable_semantic_engine:
            try:
                from vanguard_signal.semantic.drift import get_entity_drift_score
                drift_score = await get_entity_drift_score(entity_value, self._session)
            except Exception as drift_exc:
                logger.debug("Drift score unavailable: %s", drift_exc)

        confidence, source_weights = await self.build_confidence_score(
            ensemble_result.ensemble_score,
            series_row.source_id,
            semantic_drift=drift_score,
        )

        # 2. Severity
        severity = compute_severity(confidence)

        # 3. Create Alert
        now = datetime.now(timezone.utc)
        alert = Alert(
            primary_entity=entity_value,
            related_entities=None,
            anomaly_result_id=anomaly_row.id,
            severity=severity,
            status=AlertStatus.ACTIVE,
            confidence_score=round(confidence, 4),
            ensemble_anomaly_score=ensemble_result.ensemble_score,
            source_weights=source_weights,
            semantic_drift_score=round(drift_score, 4),
            reason_code=ensemble_result.reason_code,
            summary_text=ensemble_result.summary,
            signal_start=series_row.bucket_start,
            signal_end=series_row.bucket_end,
        )
        self._session.add(alert)
        await self._session.flush()  # get alert.id

        # 3.5. Select and apply alert template
        template_service = AlertTemplateService(self._session)
        template = await template_service.get_template_for_alert(alert)
        if template:
            rendered_content = template_service.render_template(template, alert)
            # Store template information in alert metadata or create a related record
            # For now, we'll store the rendered subject in a new field if we add it later
            # For backward compatibility, we keep the auto-generated summary_text
            logger.debug("Applied template '%s' to alert %s", template.name, alert.id)
        else:
            logger.debug("No suitable template found for alert %s, using default content", alert.id)

        # 4. Trace evidence
        raw_ids, norm_ids, series_ids, anomaly_ids = await self.trace_evidence(
            series_row, anomaly_row
        )

        # 5. Create EvidenceChain
        evidence_text = (
            f"Alert triggered for '{entity_value}'. "
            f"Ensemble anomaly score: {ensemble_result.ensemble_score:.3f}. "
            f"Confidence: {confidence:.3f} (severity: {severity.value}). "
            f"Evidence path: {len(raw_ids)} raw payloads → "
            f"{len(norm_ids)} normalized events → "
            f"{len(series_ids)} time-series buckets → "
            f"{len(anomaly_ids)} anomaly results. "
            f"Reason: {ensemble_result.reason_code}. "
            f"Detail: {ensemble_result.summary}"
        )

        evidence = EvidenceChain(
            alert_id=alert.id,
            raw_ids=raw_ids,
            normalized_event_ids=norm_ids,
            series_ids=series_ids,
            anomaly_ids=anomaly_ids,
            explainability_text=evidence_text,
            evidence_metadata={
                "stl_details": ensemble_result.stl.details,
                "iforest_details": ensemble_result.iforest.details,
                "cusum_details": ensemble_result.cusum.details,
                "weights": {
                    "stl": ensemble_result.weight_stl,
                    "iforest": ensemble_result.weight_iforest,
                    "cusum": ensemble_result.weight_cusum,
                },
            },
        )
        self._session.add(evidence)
        await self._session.flush()

        logger.warning(
            "🚨 ALERT CREATED: id=%s entity='%s' severity=%s confidence=%.3f",
            alert.id,
            entity_value,
            severity.value,
            confidence,
        )

        return alert
