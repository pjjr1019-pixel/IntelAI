"""
base.py — SQLAlchemy declarative base & reusable column mixins.

Every table inherits from `Base`.
Most tables also inherit from `TimestampMixin` (created/updated)
and `AuditMixin` (created_by / updated_by) so every row is traceable
for government audit requirements.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ── Declarative Base ─────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Root base class for every ORM model in Vanguard Signal.
    All tables share a UUID primary key.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique row identifier",
    )


# ── Mixins ───────────────────────────────────────────────────────────────

class TimestampMixin:
    """Automatically managed created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
        comment="Row creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
        comment="Last modification timestamp (UTC)",
    )


class AuditMixin:
    """
    Captures WHO created / modified each row.
    In production this is populated from the JWT subject claim.
    """

    created_by: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment="User or service principal that created the row",
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment="User or service principal that last modified the row",
    )
