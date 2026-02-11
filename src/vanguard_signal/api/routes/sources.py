"""
sources.py — Source registry management endpoints.

Endpoints:
  GET    /api/sources          — List all registered data sources
  POST   /api/sources          — Register a new data source
  GET    /api/sources/{id}     — Get source details + health status
  PATCH  /api/sources/{id}     — Update source config
  GET    /api/sources/health   — Health overview of all sources with weights
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db, get_user_id
from vanguard_signal.ingestion.health import SourceHealthMonitor
from vanguard_signal.schema.models.ingestion import SourceRegistry
from vanguard_signal.schema.validators import (
    SourceRegistryCreate,
    SourceRegistryRead,
    SourceRegistryUpdate,
)

router = APIRouter(prefix="/api/sources", tags=["sources"])


# ── List Sources ─────────────────────────────────────────────────────────

@router.get("", response_model=list[SourceRegistryRead])
async def list_sources(
    db: AsyncSession = Depends(get_db),
) -> list[SourceRegistryRead]:
    """Return all registered data sources."""
    result = await db.execute(
        select(SourceRegistry).order_by(SourceRegistry.name)
    )
    return [SourceRegistryRead.model_validate(s) for s in result.scalars().all()]


# ── Register New Source ──────────────────────────────────────────────────

@router.post("", response_model=SourceRegistryRead, status_code=201)
async def create_source(
    body: SourceRegistryCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> SourceRegistryRead:
    """Register a new data source connector."""
    # Check for name collision
    existing = await db.execute(
        select(SourceRegistry).where(SourceRegistry.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Source '{body.name}' already exists")

    source = SourceRegistry(
        name=body.name,
        source_type=body.source_type,
        description=body.description,
        api_endpoint=body.api_endpoint,
        auth_method=body.auth_method,
        update_frequency_seconds=body.update_frequency_seconds,
        data_latency_seconds=body.data_latency_seconds,
        default_weight=body.default_weight,
        is_active=body.is_active,
        created_by=user_id,
    )
    db.add(source)
    await db.flush()
    return SourceRegistryRead.model_validate(source)


# ── Get Source Detail ────────────────────────────────────────────────────

@router.get("/health", response_model=dict)
async def source_health_overview(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Health dashboard: all sources with current status, failure counts,
    and dynamically computed confidence weights.
    """
    result = await db.execute(select(SourceRegistry))
    sources = list(result.scalars().all())

    weights = SourceHealthMonitor.compute_all_weights(sources)

    return {
        "sources": [
            {
                "name": s.name,
                "health_status": s.health_status.value,
                "consecutive_failures": s.consecutive_failures,
                "last_ingested_at": (
                    s.last_ingested_at.isoformat() if s.last_ingested_at else None
                ),
                "is_active": s.is_active,
                "default_weight": s.default_weight,
                "effective_weight": round(weights.get(s.name, 0.0), 4),
            }
            for s in sources
        ],
        "weights_normalized": weights,
    }


@router.get("/{source_id}", response_model=SourceRegistryRead)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SourceRegistryRead:
    """Get a single source by ID."""
    source = await db.get(SourceRegistry, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceRegistryRead.model_validate(source)


# ── Update Source ────────────────────────────────────────────────────────

@router.patch("/{source_id}", response_model=SourceRegistryRead)
async def update_source(
    source_id: UUID,
    body: SourceRegistryUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> SourceRegistryRead:
    """Update source configuration (weight, frequency, active toggle, etc.)."""
    source = await db.get(SourceRegistry, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    source.updated_by = user_id

    await db.flush()
    return SourceRegistryRead.model_validate(source)
