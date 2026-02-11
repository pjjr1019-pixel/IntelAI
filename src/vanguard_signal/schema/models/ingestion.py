"""
ingestion.py — Phase 1 models for the Data Lakehouse ingestion layer.

Tables
------
SourceRegistry   – Metadata about each external data connector.
RawIngestion     – Immutable, bit-for-bit copy of every API response.
NormalizedEvent  – Cleaned, schema-conformant events ready for analysis.

Audit guarantee: every NormalizedEvent points back to its RawIngestion
row, and every RawIngestion carries a SHA-256 hash of the payload so
analysts (or auditors) can verify nothing was altered post-ingest.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vanguard_signal.schema.base import AuditMixin, Base, TimestampMixin
from vanguard_signal.schema.enums import EntityType, HealthStatus, SourceType


# ═════════════════════════════════════════════════════════════════════════
# 1. SOURCE REGISTRY — "What feeds do we have?"
# ═════════════════════════════════════════════════════════════════════════

class SourceRegistry(Base, TimestampMixin, AuditMixin):
    """
    One row per external data connector (Google Trends, Wikipedia, etc.).

    The `health_status` is updated by the ingestion scheduler every cycle.
    When a source transitions to DEGRADED or DOWN the confidence
    re-weighting engine reads this table to adjust alert scores.
    """

    __tablename__ = "source_registry"
    __table_args__ = (
        UniqueConstraint("name", name="uq_source_name"),
        {"schema": "ingestion", "comment": "Catalogue of all data sources"},
    )

    # ── Identity ─────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(128), nullable=False,
        comment="Human-readable source name, e.g. 'google_trends'",
    )
    source_type: Mapped[SourceType] = mapped_column(
        nullable=False,
        comment="Broad category: search / wiki / social / news / …",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Free-text notes about the source",
    )

    # ── Connection ───────────────────────────────────────────────────────
    api_endpoint: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
        comment="Base URL or ARN of the external API",
    )
    auth_method: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="oauth2 | api_key | iam_role | none",
    )

    # ── Scheduling ───────────────────────────────────────────────────────
    update_frequency_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3600,
        comment="How often (seconds) the connector runs",
    )
    data_latency_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Typical delay between real-world event and availability",
    )

    # ── Health ───────────────────────────────────────────────────────────
    health_status: Mapped[HealthStatus] = mapped_column(
        nullable=False, default=HealthStatus.LIVE,
        comment="Current operational state: live / degraded / down",
    )
    last_ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp of the most recent successful data pull",
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Rolling failure count; resets on success",
    )

    # ── Weight for Confidence Re-calculation ─────────────────────────────
    default_weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0,
        comment="Baseline weight used in ensemble confidence scoring",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Master on/off switch for this connector",
    )

    # ── Relationships ────────────────────────────────────────────────────
    raw_ingestions: Mapped[list["RawIngestion"]] = relationship(
        back_populates="source", lazy="selectin",
    )
    news_articles: Mapped[list["NewsArticle"]] = relationship(
        back_populates="source", lazy="selectin",
    )


# ═════════════════════════════════════════════════════════════════════════
# 2. RAW INGESTION — Immutable "Data Lake" layer
# ═════════════════════════════════════════════════════════════════════════

class RawIngestion(Base, TimestampMixin):
    """
    Bit-for-bit capture of every API response.

    This table is APPEND-ONLY. Rows are never updated or deleted.
    The `payload_hash` (SHA-256) lets auditors verify integrity at any
    future date.  `schema_version` tracks breaking changes in the
    upstream API so downstream parsers know which decoder to use.
    """

    __tablename__ = "raw_ingestion"
    __table_args__ = (
        Index("ix_raw_source_time", "source_id", "ingested_at"),
        {"schema": "ingestion", "comment": "Immutable raw API payloads"},
    )

    # ── Foreign Keys ─────────────────────────────────────────────────────
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Which source produced this payload",
    )

    # ── Payload ──────────────────────────────────────────────────────────
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When VanguardSignal received this data",
    )
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Complete API response body stored as JSONB",
    )
    payload_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 hex digest of the raw payload bytes",
    )
    payload_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Byte length of the original payload",
    )

    # ── Schema Versioning ────────────────────────────────────────────────
    schema_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="1.0",
        comment="Version tag for the upstream API schema",
    )

    # ── Data Quality Flags ───────────────────────────────────────────────
    is_valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="False if schema validation failed at ingest",
    )
    validation_errors: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Structured list of validation failures, if any",
    )

    # ── Relationships ────────────────────────────────────────────────────
    source: Mapped["SourceRegistry"] = relationship(
        back_populates="raw_ingestions",
    )
    normalized_events: Mapped[list["NormalizedEvent"]] = relationship(
        back_populates="raw_record", lazy="selectin",
    )
    news_articles: Mapped[list["NewsArticle"]] = relationship(
        back_populates="raw_record", lazy="selectin",
    )


# ═════════════════════════════════════════════════════════════════════════
# 3. NORMALIZED EVENT — Cleaned, analysis-ready rows
# ═════════════════════════════════════════════════════════════════════════

class NormalizedEvent(Base, TimestampMixin):
    """
    One row per discrete, cleaned observation extracted from a raw
    payload.  A single RawIngestion row may yield many
    NormalizedEvents (e.g. one Google Trends response → multiple
    keyword/timepoint tuples).

    `raw_id` provides the unbreakable audit trail back to the
    original data.
    """

    __tablename__ = "normalized_event"
    __table_args__ = (
        Index("ix_norm_entity_time", "entity_type", "event_time"),
        Index("ix_norm_source_time", "source_id", "event_time"),
        Index("ix_norm_entity_value", "entity_value"),
        {"schema": "ingestion", "comment": "Cleaned, schema-conformant events"},
    )

    # ── Provenance ───────────────────────────────────────────────────────
    raw_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion.raw_ingestion.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Link back to the immutable raw payload (audit trail)",
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Denormalized source FK for fast filtering",
    )

    # ── Event Description ────────────────────────────────────────────────
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When the event actually occurred (source timestamp)",
    )
    entity_type: Mapped[EntityType] = mapped_column(
        nullable=False,
        comment="Kind of entity: search_query / wiki_page / …",
    )
    entity_value: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="The search term, page title, headline text, etc.",
    )
    metric_value: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Numeric measure: search interest, page views, sentiment, …",
    )

    # ── Optional Enrichment ──────────────────────────────────────────────
    geo: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
        comment="ISO 3166-1 alpha-2 country code, if available",
    )
    language: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
        comment="ISO 639-1 language code, if available",
    )
    metadata_extra: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Catch-all for source-specific fields not in the schema",
    )

    # ── Relationships ────────────────────────────────────────────────────
    raw_record: Mapped["RawIngestion"] = relationship(
        back_populates="normalized_events",
    )


# ═════════════════════════════════════════════════════════════════════════
# 4. NEWS ARTICLES — Structured news content for narrative analysis
# ═════════════════════════════════════════════════════════════════════════

class NewsArticle(Base, TimestampMixin):
    """
    Structured news articles for narrative saturation analysis.

    This model represents processed news articles with extracted
    titles, summaries, and metadata for semantic analysis.
    """

    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_published", "published_at"),
        Index("ix_news_source", "source_id"),
        {"schema": "ingestion", "comment": "Structured news articles for analysis"},
    )

    # ── Identity ─────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(512), nullable=False,
        comment="Article headline or title",
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Article summary or excerpt",
    )
    url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
        comment="Original article URL",
    )

    # ── Provenance ───────────────────────────────────────────────────────
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Source that provided this article",
    )
    raw_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion.raw_ingestion.id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to raw ingestion record if available",
    )

    # ── Timing ───────────────────────────────────────────────────────────
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When the article was published",
    )

    # ── Content Metadata ─────────────────────────────────────────────────
    author: Mapped[str | None] = mapped_column(
        String(256), nullable=True,
        comment="Article author if available",
    )
    language: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
        comment="ISO 639-1 language code",
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Sentiment analysis score (-1 to 1)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    source: Mapped["SourceRegistry"] = relationship(
        back_populates="news_articles",
    )
    raw_record: Mapped["RawIngestion"] = relationship(
        back_populates="news_articles",
    )
    # narrative_clusters: Mapped[List["NarrativeCluster"]] = relationship(
    #     secondary="narrative_cluster_articles",
    #     back_populates="articles",
    # )
