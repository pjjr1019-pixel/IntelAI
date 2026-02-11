"""trending_history.py — Endpoints to fetch historical trend timeseries.

This endpoint first attempts to read historical `NormalizedEvent` rows
for the given `keyword` (entity_value) from the ingestion schema. If no
records are found, it falls back to a live Google Trends preview using the
existing connector (same logic as the `google_trends.preview` route).

GET /api/trending/history/{keyword}?geo=US&days=30
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.api.auth import require_auth
from vanguard_signal.schema.models.ingestion import NormalizedEvent, SourceRegistry
from vanguard_signal.schema.enums import EntityType
from vanguard_signal.ingestion.connectors.google_trends import GoogleTrendsConnector


router = APIRouter(prefix="/api/trending", tags=["trending"])


@router.get("/history/{keyword}", response_model=Any)
async def get_keyword_history(
    keyword: str,
    geo: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
) -> Any:
    """Return historical time series for a keyword.

    Tries to query `NormalizedEvent` rows (source=google_trends, entity_type=search_query).
    If none are present, performs a live preview using the GoogleTrendsConnector.
    """

    # Query normalized events for this keyword and source
    stmt = (
        select(NormalizedEvent)
        .join(SourceRegistry, NormalizedEvent.source_id == SourceRegistry.id)
        .where(NormalizedEvent.entity_type == EntityType.SEARCH_QUERY)
        .where(NormalizedEvent.entity_value == keyword)
        .where(SourceRegistry.name == "google_trends")
    )
    if geo:
        stmt = stmt.where(NormalizedEvent.geo == geo)

    # Limit timeframe to `days` before now
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = stmt.where(NormalizedEvent.event_time >= since)
    stmt = stmt.order_by(NormalizedEvent.event_time.asc())

    result = await db.execute(stmt)
    rows = result.scalars().all()

    if rows:
        data = [
            {"timestamp": r.event_time.isoformat(), "value": r.metric_value}
            for r in rows
        ]
        return {
            "keyword": keyword,
            "geo": geo or "global",
            "data": data,
            "source": "ingestion",
            "points": len(data),
        }

    # Fallback: live preview via connector (no DB writes)
    connector = GoogleTrendsConnector()
    connector._geo = geo or ""
    connector._timeframe = f"now {days}-d"
    connector._delay = 1.0

    try:
        payload, elapsed = await connector.fetch_raw([keyword])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google Trends error: {exc}")

    interest = payload.get("interest_over_time", {})
    data_points = [
        {"timestamp": ts, "value": list(scores.values())[0] if scores else 0}
        for ts, scores in sorted(interest.items())
    ]

    return {
        "keyword": keyword,
        "geo": geo or "global",
        "data": data_points,
        "source": "google_trends_preview",
        "elapsed_seconds": round(elapsed, 2),
    }
