"""
user.py — User accounts for authentication and authorization.

Tables
------
User  — Registered users with bcrypt-hashed passwords and role assignments.

Uses the 'alert' schema in Postgres (alongside Alert, Feedback, etc.)
since user management is part of the operational layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vanguard_signal.schema.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    Registered user with hashed credentials and role assignment.

    Roles:
        admin   — Full access (user management, settings, detection control)
        analyst — Can view alerts, submit feedback, manage watchlist
        viewer  — Read-only access to alerts and dashboards
    """

    __tablename__ = "user"
    __table_args__ = (
        Index("ix_user_username", "username", unique=True),
        Index("ix_user_email", "email", unique=True),
        {"schema": "alert"},
    )

    username: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment="Login username (unique, case-insensitive enforced at app level)",
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        comment="Email address for notifications and password recovery",
    )
    password_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="bcrypt-hashed password (never store plaintext)",
    )
    display_name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Human-readable display name",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="analyst",
        comment="Authorization role: admin | analyst | viewer",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Soft-delete flag — inactive users cannot log in",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful login",
    )
    preferences: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="User preferences and settings stored as JSON",
    )


    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="user", uselist=False)
    simulation_sessions: Mapped[list["SimulationSession"]] = relationship("SimulationSession", back_populates="user")
    risk_profile: Mapped["RiskProfile"] = relationship("RiskProfile", back_populates="user", uselist=False)
    position_size_rules: Mapped[list["PositionSizeRule"]] = relationship("PositionSizeRule", back_populates="user")
    stop_loss_rules: Mapped[list["StopLossRule"]] = relationship("StopLossRule", back_populates="user")
    circuit_breakers: Mapped[list["CircuitBreaker"]] = relationship("CircuitBreaker", back_populates="user")
    risk_alerts: Mapped[list["RiskAlert"]] = relationship("RiskAlert", back_populates="user")
    risk_metrics: Mapped[list["UserRiskMetrics"]] = relationship("UserRiskMetrics", back_populates="user")
    drawdown_limits: Mapped[list["DrawdownLimit"]] = relationship("DrawdownLimit", back_populates="user")
    diversification_rules: Mapped[list["DiversificationRule"]] = relationship("DiversificationRule", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.username!r} role={self.role}>"
