"""
dashboard.py — Aggregate statistics and summaries for the UI dashboard.

Endpoints:
  GET  /api/dashboard/overview     — Key metrics at a glance
  GET  /api/dashboard/timeline     — Alert volume over time
  GET  /api/dashboard/top-entities — Most frequently flagged entities
  GET  /api/dashboard/severity     — Breakdown by severity level
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.api.cache import cached

# PERFORMANCE: Ensure DB indexes exist for Alert.created_at, Alert.status, Alert.severity, Alert.primary_entity, and all columns used in dashboard queries. See model definitions for recommended indexes.
from vanguard_signal.schema.enums import AlertStatus, Severity
from vanguard_signal.schema.models.alert import Alert, AnalystFeedback, PostMortem
from vanguard_signal.schema.models.ingestion import NormalizedEvent, SourceRegistry
from vanguard_signal.schema.models.signal import AnomalyResult

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ── Test endpoint ───────────────────────────────────────────────────────

@router.get("/test")
async def test_endpoint():
    return {"message": "Dashboard router is working"}

# ── Overview ─────────────────────────────────────────────────────────────

@router.get("/overview")
async def dashboard_overview() -> dict:
    """
    Single-call summary for the main dashboard panel.

    Returns counts of total alerts, active alerts, avg confidence,
    source health, and recent activity.
    """
    # Temporarily return mock data to test endpoint
    now = datetime.now(timezone.utc)
    return {
        "total_alerts": 0,
        "active_alerts": 0,
        "alerts_24h": 0,
        "alerts_7d": 0,
        "avg_confidence_active": 0.0,
        "critical_high_active": 0,
        "registered_sources": 0,
        "total_events_ingested": 0,
        "generated_at": now.isoformat(),
    }


# ── Timeline ─────────────────────────────────────────────────────────────

@router.get("/timeline", response_model=dict)
@cached(ttl_seconds=300, key_prefix="dashboard")  # Cache for 5 minutes
@cached(ttl_seconds=300, key_prefix="dashboard")  # Cache for 5 minutes (unchanged)
async def alert_timeline(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Alert count per day for the last N days (for charting)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            cast(Alert.created_at, Date).label("date"),
            func.count(Alert.id).label("count"),
        )
        .where(Alert.created_at >= cutoff)
        # PERFORMANCE NOTE: Ensure DB indexes exist for Alert.created_at, Alert.status, Alert.severity, Alert.primary_entity for optimal dashboard query speed.
        .group_by(cast(Alert.created_at, Date))
        .order_by(cast(Alert.created_at, Date))
    )
    result = await db.execute(stmt)

    return {
        "days": days,
        "timeline": [
            {"date": str(row.date), "count": row.count}
            for row in result.all()
        ],
    }


# ── Top Entities ─────────────────────────────────────────────────────────

@router.get("/top-entities", response_model=dict)
async def top_entities(
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Most frequently flagged entities in the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            Alert.primary_entity,
            func.count(Alert.id).label("alert_count"),
            func.avg(Alert.confidence_score).label("avg_confidence"),
            func.max(Alert.confidence_score).label("max_confidence"),
        )
        .where(Alert.created_at >= cutoff)
        .group_by(Alert.primary_entity)
        .order_by(func.count(Alert.id).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)

    return {
        "limit": limit,
        "days": days,
        "entities": [
            {
                "entity": row.primary_entity,
                "alert_count": row.alert_count,
                "avg_confidence": round(float(row.avg_confidence), 4),
                "max_confidence": round(float(row.max_confidence), 4),
            }
            for row in result.all()
        ],
    }


# ── Severity Breakdown ───────────────────────────────────────────────────

@router.get("/severity", response_model=dict)
async def severity_breakdown(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Active alert count broken down by severity level."""
    stmt = (
        select(
            Alert.severity,
            func.count(Alert.id).label("count"),
        )
        .where(Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.WATCHING]))
        .group_by(Alert.severity)
    )
    result = await db.execute(stmt)

    breakdown = {sev.value: 0 for sev in Severity}
    for row in result.all():
        breakdown[row.severity.value] = row.count

    return {"breakdown": breakdown}
