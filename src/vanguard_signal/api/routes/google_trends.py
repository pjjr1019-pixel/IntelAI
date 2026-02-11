"""
google_trends.py — Google Trends exploration endpoints.

Endpoints:
  POST /api/sources/google-trends/preview  — Fetch live Google Trends data
                                              for selected keywords (no DB write)
  POST /api/sources/google-trends/ingest   — Fetch + store into the ingestion
                                              pipeline (DB write)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db, get_user_id
from vanguard_signal.ingestion.connectors.google_trends import GoogleTrendsConnector

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sources/google-trends",
    tags=["google-trends"],
)


# ── Request / Response Models ────────────────────────────────────────────

class TrendsPreviewRequest(BaseModel):
    keywords: list[str] = Field(..., min_length=1, max_length=20)
    timeframe: str = Field("now 7-d", max_length=30)
    geo: str = Field("", max_length=8)


class TrendDataPoint(BaseModel):
    timestamp: str
    scores: dict[str, int]


class TrendsPreviewResponse(BaseModel):
    keywords: list[str]
    timeframe: str
    geo: str
    data_points: list[TrendDataPoint]
    total_points: int
    elapsed_seconds: float


class TrendsIngestResponse(BaseModel):
    status: str
    keywords: list[str]
    events_created: int
    elapsed_seconds: float


# ── Preview (read-only, no DB) ───────────────────────────────────────────

@router.post("/preview", response_model=TrendsPreviewResponse)
async def preview_trends(body: TrendsPreviewRequest) -> TrendsPreviewResponse:
    """
    Fetch live Google Trends data for the given keywords without storing
    anything. Ideal for exploration and preview before committing to
    the ingestion pipeline.
    """
    connector = GoogleTrendsConnector()
    # Override connector settings from the request
    connector._timeframe = body.timeframe
    connector._geo = body.geo
    connector._delay = 1.0  # faster for preview

    try:
        payload, elapsed = await connector.fetch_raw(body.keywords)
    except Exception as exc:
        logger.error("Google Trends preview failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Google Trends API error: {exc}")

    interest = payload.get("interest_over_time", {})

    data_points = [
        TrendDataPoint(timestamp=ts, scores=scores)
        for ts, scores in sorted(interest.items())
    ]

    return TrendsPreviewResponse(
        keywords=body.keywords,
        timeframe=body.timeframe,
        geo=body.geo or "worldwide",
        data_points=data_points,
        total_points=len(data_points),
        elapsed_seconds=round(elapsed, 2),
    )


# ── Ingest (fetch + store to DB) ────────────────────────────────────────

@router.post("/ingest", response_model=TrendsIngestResponse)
async def ingest_trends(
    body: TrendsPreviewRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> TrendsIngestResponse:
    """
    Fetch Google Trends data for the given keywords AND store it into
    the ingestion pipeline (raw + normalized events).
    """
    from vanguard_signal.ingestion.storage import IngestionStore
    from vanguard_signal.schema.enums import SourceType
    from vanguard_signal.schema.validators import SourceRegistryCreate

    connector = GoogleTrendsConnector()
    connector._timeframe = body.timeframe
    connector._geo = body.geo
    connector._delay = 1.0

    store = IngestionStore(db)

    # Ensure google_trends source exists
    src_def = SourceRegistryCreate(
        name="google_trends",
        source_type=SourceType.SEARCH,
        description="Google Trends interest-over-time via pytrends",
        update_frequency_seconds=3600,
        data_latency_seconds=300,
        default_weight=1.0,
    )
    source = await store.get_or_create_source(src_def)

    try:
        payload, elapsed = await connector.fetch_raw(body.keywords)
    except Exception as exc:
        logger.error("Google Trends ingest failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Google Trends API error: {exc}")

    # Store raw
    raw_create = connector.build_raw_ingestion(source.id, payload)
    raw_row = await store.store_raw(raw_create)

    # Normalize + store events
    events = connector.normalize(payload, raw_row.id, source.id)
    if events:
        await store.store_events(events)

    return TrendsIngestResponse(
        status="completed",
        keywords=body.keywords,
        events_created=len(events),
        elapsed_seconds=round(elapsed, 2),
    )
