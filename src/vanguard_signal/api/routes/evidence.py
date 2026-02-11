"""
evidence.py — Evidence chain retrieval.

Endpoints:
  GET  /api/evidence/{alert_id}  — Get all evidence chains for an alert
  GET  /api/evidence/trace/{id}  — Get a single evidence chain with full lineage
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.schema.models.alert import EvidenceChain
from vanguard_signal.schema.models.ingestion import NormalizedEvent, RawIngestion
from vanguard_signal.schema.models.signal import AnomalyResult, SignalTimeSeries
from vanguard_signal.schema.validators import EvidenceChainRead

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/{alert_id}", response_model=list[EvidenceChainRead])
async def get_evidence_for_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[EvidenceChainRead]:
    """Return all evidence chains linked to an alert."""
    stmt = select(EvidenceChain).where(EvidenceChain.alert_id == alert_id)
    result = await db.execute(stmt)
    chains = result.scalars().all()
    return [EvidenceChainRead.model_validate(c) for c in chains]


@router.get("/trace/{evidence_id}", response_model=dict)
async def trace_evidence(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Full lineage trace: resolves every UUID in the evidence chain
    back to the actual data rows.  This is the "audit deep-dive" endpoint.

    Returns the evidence chain + resolved raw payloads, events, series,
    and anomaly results.
    """
    chain = await db.get(EvidenceChain, evidence_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Evidence chain not found")

    # Resolve raw ingestion rows
    raw_rows = []
    for rid in chain.raw_ids:
        try:
            row = await db.get(RawIngestion, UUID(rid))
            if row:
                raw_rows.append({
                    "id": str(row.id),
                    "source_id": str(row.source_id),
                    "ingested_at": row.ingested_at.isoformat(),
                    "payload_hash": row.payload_hash,
                    "payload_size_bytes": row.payload_size_bytes,
                    "is_valid": row.is_valid,
                })
        except Exception:
            pass

    # Resolve normalized events
    event_rows = []
    for eid in chain.normalized_event_ids:
        try:
            row = await db.get(NormalizedEvent, UUID(eid))
            if row:
                event_rows.append({
                    "id": str(row.id),
                    "event_time": row.event_time.isoformat(),
                    "entity_type": row.entity_type.value,
                    "entity_value": row.entity_value,
                    "metric_value": row.metric_value,
                    "geo": row.geo,
                })
        except Exception:
            pass

    # Resolve series rows
    series_rows = []
    for sid in chain.series_ids:
        try:
            row = await db.get(SignalTimeSeries, UUID(sid))
            if row:
                series_rows.append({
                    "id": str(row.id),
                    "entity_value": row.entity_value,
                    "bucket_size": row.bucket_size.value,
                    "bucket_start": row.bucket_start.isoformat(),
                    "value": row.value,
                    "sample_count": row.sample_count,
                    "coverage_score": row.coverage_score,
                })
        except Exception:
            pass

    # Resolve anomaly rows
    anomaly_rows = []
    for aid in chain.anomaly_ids:
        try:
            row = await db.get(AnomalyResult, UUID(aid))
            if row:
                anomaly_rows.append({
                    "id": str(row.id),
                    "ensemble_score": row.ensemble_score,
                    "is_anomaly": row.is_anomaly,
                    "stl_residual_zscore": row.stl_residual_zscore,
                    "iforest_score": row.iforest_score,
                    "cusum_score": row.cusum_score,
                    "weight_stl": row.weight_stl,
                    "weight_iforest": row.weight_iforest,
                    "weight_cusum": row.weight_cusum,
                })
        except Exception:
            pass

    return {
        "evidence_chain": EvidenceChainRead.model_validate(chain),
        "explainability_text": chain.explainability_text,
        "lineage": {
            "raw_ingestions": raw_rows,
            "normalized_events": event_rows,
            "time_series": series_rows,
            "anomaly_results": anomaly_rows,
        },
        "evidence_metadata": chain.evidence_metadata,
    }
