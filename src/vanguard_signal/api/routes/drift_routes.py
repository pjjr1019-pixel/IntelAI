"""
drift_routes.py — Semantic drift monitoring API routes.

Endpoints:
  GET /api/semantic/drift           — Get drifting clusters
  GET /api/semantic/drift/{entity}  — Get drift score for a specific entity
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.config import settings

router = APIRouter(prefix="/api/semantic", tags=["semantic"])
logger = logging.getLogger(__name__)


@router.get("/drift", response_model=dict)
async def get_drifting_clusters(
    lookback_hours: int = Query(168, ge=1),
    min_drift: float = Query(0.1, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return clusters with significant semantic drift."""
    if not settings.enable_semantic_engine:
        return {"enabled": False, "clusters": [], "message": "Semantic engine is disabled"}

    from vanguard_signal.semantic.drift import get_drifting_clusters as _get_clusters
    clusters = await _get_clusters(db, lookback_hours=lookback_hours, min_drift=min_drift)
    return {"enabled": True, "total": len(clusters), "clusters": clusters}


@router.get("/drift/{entity}", response_model=dict)
async def get_entity_drift(
    entity: str,
    lookback_hours: int = Query(168, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the drift score for a specific entity."""
    if not settings.enable_semantic_engine:
        return {"enabled": False, "entity": entity, "drift_score": 0.0}

    from vanguard_signal.semantic.drift import get_entity_drift_score
    score = await get_entity_drift_score(entity, db, lookback_hours=lookback_hours)
    return {"enabled": True, "entity": entity, "drift_score": round(score, 4)}
