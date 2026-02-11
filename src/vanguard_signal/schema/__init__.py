# ── Vanguard Signal — Data Schema Package ────────────────────────────────
#
# This package contains every database model, enumeration, and Pydantic
# validation schema used by the platform.  It is the single source of
# truth for how data is stored, validated, and traced for audit.
#
# Sub-modules
# -----------
# enums        – Controlled vocabularies (SourceType, Severity, …)
# base         – SQLAlchemy declarative base & common mixins
# models       – ORM table definitions (all 12 core entities)
# validators   – Pydantic schemas for API / ingestion validation
# database     – Engine creation, session factory, migration helpers
# ─────────────────────────────────────────────────────────────────────────

from vanguard_signal.schema.base import Base, TimestampMixin, AuditMixin
from vanguard_signal.schema.enums import (
    SourceType,
    HealthStatus,
    EntityType,
    Severity,
    AlertStatus,
    FeedbackVerdict,
    ImpactDomain,
    EventOutcome,
    TimeBucket,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "AuditMixin",
    # enums
    "SourceType",
    "HealthStatus",
    "EntityType",
    "Severity",
    "AlertStatus",
    "FeedbackVerdict",
    "ImpactDomain",
    "EventOutcome",
    "TimeBucket",
]
