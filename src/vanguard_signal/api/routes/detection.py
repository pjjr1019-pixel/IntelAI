"""
detection.py — Manual trigger endpoints for ingestion and detection cycles.

Endpoints:
  POST /api/detection/ingest  — Trigger one ingestion cycle now
  POST /api/detection/run     — Trigger one detection cycle now
  POST /api/detection/full    — Run ingestion + detection back-to-back
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.schema.enums import TimeBucket

router = APIRouter(prefix="/api/detection", tags=["detection"])
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=dict)
async def trigger_ingestion() -> dict:
    """
    Manually trigger one ingestion cycle (all active sources).
    Useful for testing or on-demand data refresh.
    """
    from vanguard_signal.ingestion.scheduler import run_ingestion_cycle

    logger.info("Manual ingestion cycle triggered via API")
    summaries = await run_ingestion_cycle()

    return {
        "status": "completed",
        "sources": summaries,
        "total_events": sum(s.get("events", 0) for s in summaries),
    }


@router.post("/run", response_model=dict)
async def trigger_detection(
    bucket: str = Query("day", pattern="^(hour|day|week|month)$"),
    threshold: float = Query(0.6, ge=0.0, le=1.0),
    min_points: int = Query(7, ge=3),
) -> dict:
    """
    Manually trigger one anomaly detection cycle.
    Aggregates recent events, runs ensemble detection on all entities.
    """
    from vanguard_signal.detection.pipeline import run_detection_cycle

    bucket_map = {
        "hour": TimeBucket.HOUR,
        "day": TimeBucket.DAY,
        "week": TimeBucket.WEEK,
        "month": TimeBucket.MONTH,
    }

    logger.info("Manual detection cycle triggered via API (bucket=%s, threshold=%s)", bucket, threshold)
    result = await run_detection_cycle(
        bucket_size=bucket_map[bucket],
        min_series_length=min_points,
        ensemble_threshold=threshold,
    )

    return {
        "status": "completed",
        "result": result,
    }


@router.post("/full", response_model=dict)
async def trigger_full_cycle(
    bucket: str = Query("day", pattern="^(hour|day|week|month)$"),
    threshold: float = Query(0.6, ge=0.0, le=1.0),
) -> dict:
    """
    Run the full pipeline: ingestion → detection in sequence.
    This is the "do everything once" button.
    """
    from vanguard_signal.detection.pipeline import run_detection_cycle
    from vanguard_signal.ingestion.scheduler import run_ingestion_cycle

    bucket_map = {
        "hour": TimeBucket.HOUR,
        "day": TimeBucket.DAY,
        "week": TimeBucket.WEEK,
        "month": TimeBucket.MONTH,
    }

    logger.info("Full cycle triggered via API")

    # Step 1: Ingest
    ingest_summaries = await run_ingestion_cycle()

    # Step 2: Detect
    detection_result = await run_detection_cycle(
        bucket_size=bucket_map[bucket],
        ensemble_threshold=threshold,
    )

    return {
        "status": "completed",
        "ingestion": {
            "sources": ingest_summaries,
            "total_events": sum(s.get("events", 0) for s in ingest_summaries),
        },
        "detection": detection_result,
    }
