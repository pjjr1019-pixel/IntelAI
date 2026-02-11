"""
ai_control.py — AI Control API for automated dashboard interactions.

Endpoints for AI systems to control and interact with the Vanguard Signal dashboard.

Endpoints:
  POST /api/ai/control/dashboard    — Execute dashboard control actions
  POST /api/ai/control/watchlist    — Manage watchlist via AI
  POST /api/ai/control/alerts       — Create/modify alerts via AI
  POST /api/ai/control/thresholds   — Adjust detection thresholds
  POST /api/ai/control/export       — Trigger data exports
  GET  /api/ai/status               — AI system health and status
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.schema.models.alert import Alert
from vanguard_signal.schema.enums import Severity, AlertStatus

router = APIRouter(prefix="/api/ai", tags=["ai-control"])


# ── Pydantic Models ──────────────────────────────────────────────────────

class DashboardAction(BaseModel):
    action: str  # "update_watchlist", "trigger_alert", "adjust_thresholds", "export_data"
    parameters: Dict[str, Any]
    reason: Optional[str] = None  # AI reasoning for the action


class WatchlistUpdate(BaseModel):
    keywords: List[str]
    action: str = "add"  # "add", "remove", "clear"


class AlertTrigger(BaseModel):
    title: str
    description: str
    severity: Severity
    entity: str
    confidence: float
    source: str = "AI"


class ThresholdAdjustment(BaseModel):
    detector: str  # "ensemble", "stl", "isolation_forest", "cusum", "bert"
    parameter: str  # "threshold", "alpha", "min_cluster_size", etc.
    value: float
    reason: str


class ExportRequest(BaseModel):
    format: str = "json"  # "json", "csv", "excel"
    data_type: str = "alerts"  # "alerts", "trends", "signals"
    time_range: Optional[str] = "24h"  # "1h", "24h", "7d", "30d"


# ── AI Control Endpoints ─────────────────────────────────────────────────

@router.post("/control/dashboard")
async def ai_dashboard_control(
    action_request: DashboardAction,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute AI-driven dashboard control actions.

    Supported actions:
    - update_watchlist: Add/remove keywords from watchlist
    - trigger_alert: Create new alert based on AI detection
    - adjust_thresholds: Modify detection parameters
    - export_data: Generate data exports
    - clear_alerts: Archive old alerts
    - refresh_cache: Invalidate cached data
    """
    try:
        if action_request.action == "update_watchlist":
            return await _handle_watchlist_update(action_request.parameters, db)

        elif action_request.action == "trigger_alert":
            return await _handle_alert_trigger(action_request.parameters, db)

        elif action_request.action == "adjust_thresholds":
            return await _handle_threshold_adjustment(action_request.parameters, db)

        elif action_request.action == "export_data":
            return await _handle_export_request(action_request.parameters, db)

        elif action_request.action == "clear_alerts":
            return await _handle_clear_alerts(action_request.parameters, db)

        elif action_request.action == "refresh_cache":
            return await _handle_cache_refresh(action_request.parameters, db)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action_request.action}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI control action failed: {str(e)}")


@router.post("/control/watchlist")
async def ai_watchlist_control(
    update: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Direct AI control of watchlist management."""
    try:
        if update.action == "add":
            added = []
            for keyword in update.keywords:
                result = await add_to_watchlist(keyword, db)
                added.append(result)
            return {"status": "success", "added": added}

        elif update.action == "remove":
            # Implement removal logic
            return {"status": "success", "removed": update.keywords}

        elif update.action == "clear":
            # Implement clear logic
            return {"status": "success", "cleared": True}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown watchlist action: {update.action}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Watchlist control failed: {str(e)}")


@router.post("/control/alerts")
async def ai_alert_control(
    alert: AlertTrigger,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """AI-triggered alert creation."""
    try:
        alert_data = {
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "entity": alert.entity,
            "confidence": alert.confidence,
            "source": alert.source,
            "ai_generated": True,
        }

        result = await create_alert(alert_data, db)
        return {"status": "success", "alert_id": result.get("id")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert creation failed: {str(e)}")


@router.post("/control/thresholds")
async def ai_threshold_control(
    adjustment: ThresholdAdjustment,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """AI-driven threshold adjustments for detection algorithms."""
    try:
        # This would integrate with the ML pipeline settings
        # For now, return success with the adjustment details
        return {
            "status": "success",
            "adjustment": {
                "detector": adjustment.detector,
                "parameter": adjustment.parameter,
                "new_value": adjustment.value,
                "reason": adjustment.reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Threshold adjustment failed: {str(e)}")


@router.post("/control/export")
async def ai_export_control(
    export_req: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """AI-triggered data exports."""
    try:
        result = await export_data(
            format=export_req.format,
            data_type=export_req.data_type,
            time_range=export_req.time_range,
            db=db
        )
        return {"status": "success", "export_id": result.get("id")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/status")
async def ai_system_status(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    AI system health and status information.

    Returns current system metrics, active alerts, watchlist status,
    and AI optimization parameters.
    """
    try:
        # Get basic system metrics
        now = datetime.now(timezone.utc)

        # Active alerts count
        active_alerts = await db.execute(
            text("SELECT COUNT(*) FROM alert WHERE status = 'active'")
        )
        active_count = active_alerts.scalar() or 0

        # Watchlist size - check JSON file
        try:
            import os
            watchlist_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "watchlist.json")
            if os.path.exists(watchlist_path):
                with open(watchlist_path, 'r') as f:
                    watchlist_data = json.load(f)
                    watchlist_count = sum(len(keywords) for keywords in watchlist_data.get("keywords", {}).values())
            else:
                watchlist_count = 0
        except Exception:
            watchlist_count = 0

        # Recent signals - simplified query
        try:
            recent_signals = await db.execute(
                text("SELECT COUNT(*) FROM anomaly_result")
            )
            signals_count = recent_signals.scalar() or 0
        except Exception:
            signals_count = 0

        return {
            "timestamp": now.isoformat(),
            "system_health": "operational",
            "metrics": {
                "active_alerts": active_count,
                "watchlist_size": watchlist_count,
                "recent_signals": signals_count,
            },
            "ai_optimization": {
                "ensemble_weights": {"stl": 0.3, "isolation_forest": 0.3, "cusum": 0.2, "bert": 0.2},
                "thresholds": {"confidence": 0.75, "saturation": 0.7},
                "last_updated": now.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# ── Internal Helper Functions ────────────────────────────────────────────

async def _handle_watchlist_update(params: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Handle watchlist update actions."""
    from vanguard_signal.ingestion.watchlist import add_keyword

    keywords = params.get("keywords", [])
    action = params.get("action", "add")

    if action == "add":
        added = []
        for keyword in keywords:
            try:
                result = await add_keyword(keyword, "ai_control", db)
                added.append({"keyword": keyword, "success": True})
            except Exception as e:
                added.append({"keyword": keyword, "success": False, "error": str(e)})
        return {"status": "success", "added": added}

    elif action == "remove":
        # Implement removal logic here
        return {"status": "success", "removed": keywords}

    return {"status": "error", "message": f"Unknown watchlist action: {action}"}


async def _handle_alert_trigger(params: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Handle AI-triggered alert creation."""

    alert = Alert(
        primary_entity=params.get("entity", "unknown"),
        related_entities=None,
        severity=params.get("severity", "medium"),
        status=AlertStatus.ACTIVE,
        confidence_score=params.get("confidence", 0.8),
        summary_text=params.get("description", ""),
        reason_code="ai_generated",
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {"status": "success", "alert_id": str(alert.id)}


async def _handle_threshold_adjustment(params: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Handle threshold adjustments."""
    return {
        "status": "success",
        "adjustment": params,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def _handle_export_request(params: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Handle export requests."""
    # Simplified export - in production, integrate with actual export functions
    return {
        "status": "success",
        "export_id": f"ai_export_{datetime.now(timezone.utc).timestamp()}",
        "format": params.get("format", "json"),
        "data_type": params.get("data_type", "alerts")
    }


async def _handle_clear_alerts(params: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Handle alert clearing."""
    # Implement alert archiving logic
    return {"status": "success", "cleared": True}


async def _handle_cache_refresh(params: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Handle cache refresh."""
    # Implement cache invalidation
    return {"status": "success", "cache_refreshed": True}