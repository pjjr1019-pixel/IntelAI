"""
storage.py — Persistence layer for the ingestion pipeline.

Handles writing RawIngestion and NormalizedEvent rows to the database.
All writes are wrapped in transactions with proper rollback on failure.
This is the ONLY module that touches the DB during ingestion — connectors
never import SQLAlchemy directly.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.enums import HealthStatus
from vanguard_signal.schema.models.ingestion import (
    NormalizedEvent,
    RawIngestion,
    SourceRegistry,
)
from vanguard_signal.schema.validators import (
    NormalizedEventCreate,
    RawIngestionCreate,
    SourceRegistryCreate,
)

logger = logging.getLogger(__name__)


class IngestionStore:
    """
    Database access layer for ingestion operations.
    Injected with an AsyncSession from the scheduler.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Source Registry ──────────────────────────────────────────────────

    async def get_or_create_source(
        self, data: SourceRegistryCreate
    ) -> SourceRegistry:
        """
        Find a source by name, or create it if it doesn't exist.
        Returns the ORM instance (with id populated).
        """
        stmt = select(SourceRegistry).where(SourceRegistry.name == data.name)
        result = await self._session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is not None:
            return source

        source = SourceRegistry(
            name=data.name,
            source_type=data.source_type,
            description=data.description,
            api_endpoint=data.api_endpoint,
            auth_method=data.auth_method,
            update_frequency_seconds=data.update_frequency_seconds,
            data_latency_seconds=data.data_latency_seconds,
            default_weight=data.default_weight,
            is_active=data.is_active,
        )
        self._session.add(source)
        await self._session.flush()  # populates source.id
        logger.info("Created new source: %s (id=%s)", data.name, source.id)
        return source

    async def get_source_by_name(self, name: str) -> SourceRegistry | None:
        """Look up a source by its unique name."""
        stmt = select(SourceRegistry).where(SourceRegistry.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_sources(self) -> list[SourceRegistry]:
        """Return all sources that are currently enabled."""
        stmt = select(SourceRegistry).where(SourceRegistry.is_active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Raw Ingestion ────────────────────────────────────────────────────

    async def store_raw(self, data: RawIngestionCreate) -> RawIngestion:
        """
        Insert an immutable raw payload row.
        Returns the ORM instance with id populated.
        """
        row = RawIngestion(
            source_id=data.source_id,
            ingested_at=data.ingested_at,
            payload=data.payload,
            payload_hash=data.payload_hash,
            payload_size_bytes=data.payload_size_bytes,
            schema_version=data.schema_version,
        )
        self._session.add(row)
        await self._session.flush()
        logger.debug("Stored raw ingestion: id=%s, hash=%s", row.id, row.payload_hash)
        return row

    # ── Normalized Events ────────────────────────────────────────────────

    async def store_events(
        self, events: list[NormalizedEventCreate]
    ) -> list[NormalizedEvent]:
        """
        Bulk-insert normalized events.
        Returns the list of ORM instances with ids populated.
        """
        rows = [
            NormalizedEvent(
                raw_id=e.raw_id,
                source_id=e.source_id,
                event_time=e.event_time,
                entity_type=e.entity_type,
                entity_value=e.entity_value,
                metric_value=e.metric_value,
                geo=e.geo,
                language=e.language,
                metadata_extra=e.metadata_extra,
            )
            for e in events
        ]
        self._session.add_all(rows)
        await self._session.flush()
        logger.info("Stored %d normalized events", len(rows))
        return rows

    # ── Source Health Updates ─────────────────────────────────────────────

    async def update_source_health(
        self,
        source_id: UUID,
        status: HealthStatus,
        *,
        reset_failures: bool = False,
        increment_failures: bool = False,
    ) -> None:
        """Update a source's health status and failure counter."""
        from datetime import datetime, timezone

        values: dict = {"health_status": status}

        if reset_failures:
            values["consecutive_failures"] = 0
            values["last_ingested_at"] = datetime.now(timezone.utc)
        elif increment_failures:
            # Use raw SQL increment to avoid race conditions
            stmt = (
                update(SourceRegistry)
                .where(SourceRegistry.id == source_id)
                .values(
                    health_status=status,
                    consecutive_failures=SourceRegistry.consecutive_failures + 1,
                )
            )
            await self._session.execute(stmt)
            return

        stmt = (
            update(SourceRegistry)
            .where(SourceRegistry.id == source_id)
            .values(**values)
        )
        await self._session.execute(stmt)
