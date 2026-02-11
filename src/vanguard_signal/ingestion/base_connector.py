"""
base_connector.py — Abstract interface that every data connector implements.

The contract is simple:
  1. fetch_raw()    → pull data from the external API, return raw dict
  2. normalize()    → transform raw dict into a list of NormalizedEventCreate
  3. health_check() → probe if the source is alive

The scheduler calls these methods in order.  If fetch_raw() fails,
the SourceHealthMonitor downgrades the source status automatically.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from vanguard_signal.schema.enums import EntityType, HealthStatus, SourceType
from vanguard_signal.schema.validators import NormalizedEventCreate, RawIngestionCreate

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.

    Subclasses must implement:
      • source_name       (property)
      • source_type       (property)
      • entity_type       (property)
      • _fetch()          → raw API response as dict
      • _normalize_payload() → list of NormalizedEventCreate from raw data
    """

    # ── Identity (override in subclass) ──────────────────────────────────

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique machine name, e.g. 'google_trends'."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        ...

    @property
    @abstractmethod
    def entity_type(self) -> EntityType:
        ...

    # ── Core pipeline methods ────────────────────────────────────────────

    @abstractmethod
    async def _fetch(self, keywords: list[str]) -> dict[str, Any]:
        """
        Hit the external API and return the raw response body.
        Raise on unrecoverable errors; return partial data on degraded.
        """
        ...

    @abstractmethod
    def _normalize_payload(
        self,
        raw_payload: dict[str, Any],
        raw_id: UUID,
        source_id: UUID,
    ) -> list[NormalizedEventCreate]:
        """
        Convert an API response into clean NormalizedEventCreate objects.
        One raw payload may produce many events (e.g. multiple keywords × timepoints).
        """
        ...

    # ── Public orchestration (called by the scheduler) ───────────────────

    async def fetch_raw(self, keywords: list[str]) -> tuple[dict[str, Any], float]:
        """
        Fetch data and return (raw_payload, elapsed_seconds).
        """
        start = time.monotonic()
        payload = await self._fetch(keywords)
        elapsed = time.monotonic() - start
        logger.info(
            "[%s] Fetched %d bytes in %.2fs",
            self.source_name,
            len(json.dumps(payload, default=str).encode()),
            elapsed,
        )
        return payload, elapsed

    def build_raw_ingestion(
        self,
        source_id: UUID,
        payload: dict[str, Any],
    ) -> RawIngestionCreate:
        """Package the raw payload into a validated RawIngestionCreate."""
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
        return RawIngestionCreate(
            source_id=source_id,
            ingested_at=datetime.now(timezone.utc),
            payload=payload,
            payload_hash=hashlib.sha256(payload_bytes).hexdigest(),
            payload_size_bytes=len(payload_bytes),
            schema_version="1.0",
        )

    def normalize(
        self,
        raw_payload: dict[str, Any],
        raw_id: UUID,
        source_id: UUID,
    ) -> list[NormalizedEventCreate]:
        """Public wrapper around _normalize_payload with logging."""
        events = self._normalize_payload(raw_payload, raw_id, source_id)
        logger.info(
            "[%s] Normalized %d events from raw payload",
            self.source_name,
            len(events),
        )
        return events

    # ── Health Check ─────────────────────────────────────────────────────

    async def health_check(self) -> HealthStatus:
        """
        Quick probe: can we reach the API at all?
        Default implementation tries a minimal fetch.
        Override in subclass for source-specific probes.
        """
        try:
            await self._fetch(["test"])
            return HealthStatus.LIVE
        except Exception as exc:
            logger.warning("[%s] Health check failed: %s", self.source_name, exc)
            return HealthStatus.DOWN
