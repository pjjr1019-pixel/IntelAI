"""
backtest.py — API routes for triggering and viewing backtest results.

Endpoints:
  POST /api/backtest/run            — Trigger a new backtest
  GET  /api/backtest/runs           — List all backtest runs
  GET  /api/backtest/runs/{run_id}  — Get details + alerts for one run
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.config import settings
from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.enums import BacktestStatus
from vanguard_signal.schema.models.alert import BacktestRun, BacktestAlert

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = logging.getLogger(__name__)


class BacktestRequest(BaseModel):
    start_date: str = Field(..., description="ISO date string, e.g. 2025-01-01")
    end_date: str = Field(..., description="ISO date string, e.g. 2025-06-01")
    bucket: str = Field("day", pattern=r"^(hour|day|week|month)$")
    threshold: float = Field(0.6, ge=0.0, le=1.0)
    min_points: int = Field(7, ge=3)
    description: str = Field("", max_length=512)


@router.post("/run", response_model=dict)
async def trigger_backtest(body: BacktestRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Start a new backtest run over the specified time window."""
    if not settings.enable_backtest:
        raise HTTPException(status_code=400, detail="Backtesting is disabled (VS_BACKTEST=false)")

    from vanguard_signal.backtest.engine import BacktestEngine
    from vanguard_signal.schema.enums import TimeBucket

    bucket_map = {
        "hour": TimeBucket.HOUR,
        "day": TimeBucket.DAY,
        "week": TimeBucket.WEEK,
        "month": TimeBucket.MONTH,
    }

    try:
        start = datetime.fromisoformat(body.start_date).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(body.end_date).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use ISO format (YYYY-MM-DD).")

    engine = BacktestEngine(
        window_start=start,
        window_end=end,
        bucket_size=bucket_map[body.bucket],
        params={
            "ensemble_threshold": body.threshold,
            "min_series_length": body.min_points,
        },
    )

    logger.info("Backtest triggered: %s → %s", body.start_date, body.end_date)
    async with get_session() as session:
        result = await engine.run(session, description=body.description)

    return {
        "status": "completed",
        "result": result,
    }


@router.get("/runs", response_model=dict)
async def list_backtest_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all backtest runs with summary metrics."""
    count_stmt = select(func.count(BacktestRun.id))
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(BacktestRun)
        .order_by(BacktestRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "runs": [
            {
                "id": str(r.id),
                "status": r.status.value,
                "start_date": r.window_start.isoformat(),
                "end_date": r.window_end.isoformat(),
                "parameters": r.parameters,
                "precision": (r.results_summary or {}).get("precision", 0.0),
                "recall": (r.results_summary or {}).get("recall", 0.0),
                "f1": (r.results_summary or {}).get("f1_score", 0.0),
                "total_alerts": r.alerts_generated,
                "true_positives": r.true_positives,
                "false_positives": r.false_positives,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ],
    }


@router.get("/runs/{run_id}", response_model=dict)
async def get_backtest_run(run_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get a single backtest run with its generated alerts."""
    try:
        uid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    run = await db.get(BacktestRun, uid)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # Get alerts for this run
    stmt = (
        select(BacktestAlert)
        .where(BacktestAlert.backtest_run_id == uid)
        .order_by(BacktestAlert.signal_start)
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return {
        "run": {
            "id": str(run.id),
            "status": run.status.value,
            "start_date": run.window_start.isoformat(),
            "end_date": run.window_end.isoformat(),
            "parameters": run.parameters,
            "precision": (run.results_summary or {}).get("precision", 0.0),
            "recall": (run.results_summary or {}).get("recall", 0.0),
            "f1": (run.results_summary or {}).get("f1_score", 0.0),
            "total_alerts": run.alerts_generated,
            "true_positives": run.true_positives,
            "false_positives": run.false_positives,
            "missed_events": run.missed_events,
            "description": run.description,
            "created_at": run.created_at.isoformat(),
        },
        "alerts": [
            {
                "id": str(a.id),
                "entity_value": a.primary_entity,
                "detected_date": a.signal_start.isoformat(),
                "ensemble_score": a.ensemble_anomaly_score,
                "severity": a.severity.value if a.severity else None,
                "matched_real_alert_id": str(a.matched_real_alert_id) if a.matched_real_alert_id else None,
                "is_true_positive": a.is_true_positive,
            }
            for a in alerts
        ],
    }
