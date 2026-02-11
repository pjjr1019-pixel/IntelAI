"""
risk_management.py — Risk management models for position sizing, stop-loss, and safety controls.

Tables
------
RiskProfile         — User risk tolerance settings and limits
PositionSizeRule    — Position sizing algorithms and parameters
StopLossRule        — Stop-loss and take-profit automation rules
CircuitBreaker      — Market condition triggers for emergency halts
RiskAlert           — Risk violation alerts and notifications
RiskMetrics         — Real-time risk exposure tracking
DrawdownLimit       — Maximum drawdown controls and recovery
DiversificationRule — Portfolio diversification requirements

Uses the 'trading' schema for risk management data.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vanguard_signal.schema.base import Base, AuditMixin, TimestampMixin


class RiskProfile(Base, TimestampMixin, AuditMixin):
    """
    User risk tolerance profile with customizable limits and preferences.

    Defines acceptable risk levels, position sizing preferences, and safety controls.
    """

    __tablename__ = "risk_profile"
    __table_args__ = (
        Index("ix_risk_profile_user_id", "user_id", unique=True),
        Index("ix_risk_profile_is_active", "is_active"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this risk profile belongs to",
    )

    # Risk tolerance settings
    risk_tolerance: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="moderate",
        comment="Overall risk tolerance: conservative | moderate | aggressive",
    )

    max_portfolio_risk: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.02",  # 2%
        comment="Maximum portfolio risk as fraction of capital",
    )

    max_single_position_risk: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.01",  # 1%
        comment="Maximum risk per single position",
    )

    max_daily_loss: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",  # 5%
        comment="Maximum daily loss before trading halt",
    )

    max_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.10",  # 10%
        comment="Maximum drawdown before trading suspension",
    )

    # Position sizing preferences
    position_sizing_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="fixed_percentage",
        comment="Position sizing method: fixed_percentage | kelly_criterion | equal_weight",
    )

    base_position_size: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.02",  # 2%
        comment="Base position size as fraction of capital",
    )

    kelly_fraction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.5",  # Half Kelly
        comment="Kelly criterion fraction (0.5 = half Kelly)",
    )

    # Diversification settings
    max_sector_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.25",  # 25%
        comment="Maximum exposure to single sector",
    )

    max_single_stock_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",  # 5%
        comment="Maximum exposure to single stock",
    )

    min_diversification_stocks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="5",
        comment="Minimum number of stocks for diversification",
    )

    # Stop-loss settings
    use_stop_loss: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether to use stop-loss orders",
    )

    default_stop_loss_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",  # 5%
        comment="Default stop-loss percentage",
    )

    trailing_stop_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether to use trailing stops",
    )

    # Circuit breaker settings
    circuit_breaker_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether circuit breakers are enabled",
    )

    volatility_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.03",  # 3%
        comment="Volatility threshold for circuit breaker",
    )

    market_drop_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",  # 5%
        comment="Market drop threshold for circuit breaker",
    )

    # Alert preferences
    email_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether to send email alerts for risk violations",
    )

    sms_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether to send SMS alerts for critical violations",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this risk profile is active",
    )

    # Custom settings
    custom_settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Additional custom risk settings",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="risk_profile")
    alerts: Mapped[List["RiskAlert"]] = relationship("RiskAlert", back_populates="profile")

    def __repr__(self) -> str:
        return f"<RiskProfile user={self.user_id} tolerance={self.risk_tolerance}>"


class PositionSizeRule(Base, TimestampMixin, AuditMixin):
    """
    Position sizing rules for determining trade sizes based on risk parameters.

    Implements various position sizing algorithms including Kelly criterion.
    """

    __tablename__ = "position_size_rule"
    __table_args__ = (
        Index("ix_position_size_rule_user_id", "user_id"),
        Index("ix_position_size_rule_is_active", "is_active"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this rule belongs to",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Rule name for identification",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Rule description and usage notes",
    )

    # Rule type and parameters
    rule_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Rule type: fixed_percentage | kelly_criterion | volatility_adjusted | equal_risk",
    )

    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Rule-specific parameters",
    )

    # Application settings
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether this is the default rule",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this rule is active",
    )

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of times this rule has been used",
    )

    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this rule was applied",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="position_size_rules")

    def __repr__(self) -> str:
        return f"<PositionSizeRule {self.name!r} type={self.rule_type}>"


class StopLossRule(Base, TimestampMixin, AuditMixin):
    """
    Stop-loss and take-profit automation rules for position management.

    Defines conditions for automatic position closure and profit taking.
    """

    __tablename__ = "stop_loss_rule"
    __table_args__ = (
        Index("ix_stop_loss_rule_user_id", "user_id"),
        Index("ix_stop_loss_rule_is_active", "is_active"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this rule belongs to",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Rule name for identification",
    )

    # Stop-loss settings
    stop_loss_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="percentage",
        comment="Stop-loss type: percentage | fixed | trailing | volatility_based",
    )

    stop_loss_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Stop-loss trigger value (interpretation depends on type)",
    )

    # Take-profit settings
    take_profit_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether take-profit is enabled",
    )

    take_profit_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="percentage",
        comment="Take-profit type: percentage | fixed | ratio",
    )

    take_profit_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.10",  # 10%
        comment="Take-profit target value",
    )

    # Trailing stop settings
    trailing_stop_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether trailing stop is enabled",
    )

    trailing_stop_distance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",  # 5%
        comment="Trailing stop distance",
    )

    # Application settings
    auto_execute: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether to auto-execute stop orders",
    )

    notification_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether to send notifications on triggers",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this rule is active",
    )

    # Usage tracking
    trigger_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of times this rule has been triggered",
    )

    last_triggered: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this rule was triggered",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="stop_loss_rules")

    def __repr__(self) -> str:
        return f"<StopLossRule {self.name!r} stop={self.stop_loss_value}>"


class CircuitBreaker(Base, TimestampMixin, AuditMixin):
    """
    Circuit breaker rules for emergency trading halts during extreme conditions.

    Monitors market conditions and triggers automatic trading suspension.
    """

    __tablename__ = "circuit_breaker"
    __table_args__ = (
        Index("ix_circuit_breaker_user_id", "user_id"),
        Index("ix_circuit_breaker_is_active", "is_active"),
        Index("ix_circuit_breaker_triggered_at", "triggered_at"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this circuit breaker belongs to",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Circuit breaker name",
    )

    # Trigger conditions
    trigger_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Trigger type: volatility | drawdown | market_drop | correlation | custom",
    )

    trigger_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Threshold value for trigger activation",
    )

    trigger_timeframe: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="1D",
        comment="Timeframe for trigger evaluation: 1H | 4H | 1D | 1W",
    )

    # Action settings
    action_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="halt_trading",
        comment="Action type: halt_trading | reduce_positions | alert_only | custom",
    )

    action_parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Action-specific parameters",
    )

    # Recovery settings
    auto_recovery_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether automatic recovery is enabled",
    )

    recovery_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.5",  # 50% of trigger threshold
        comment="Threshold for automatic recovery",
    )

    recovery_delay_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="60",  # 1 hour
        comment="Delay before recovery attempt in minutes",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this circuit breaker is active",
    )

    is_triggered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether this circuit breaker is currently triggered",
    )

    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this circuit breaker was last triggered",
    )

    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this circuit breaker last recovered",
    )

    # Usage tracking
    trigger_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of times this breaker has been triggered",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="circuit_breakers")

    def __repr__(self) -> str:
        return f"<CircuitBreaker {self.name!r} triggered={self.is_triggered}>"


class RiskAlert(Base, TimestampMixin, AuditMixin):
    """
    Risk violation alerts and notifications for monitoring breaches.

    Tracks risk limit violations and sends appropriate notifications.
    """

    __tablename__ = "risk_alert"
    __table_args__ = (
        Index("ix_risk_alert_user_id", "user_id"),
        Index("ix_risk_alert_profile_id", "profile_id"),
        Index("ix_risk_alert_alert_type", "alert_type"),
        Index("ix_risk_alert_created_at", "created_at"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this alert belongs to",
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.risk_profile.id", ondelete="CASCADE"),
        nullable=False,
        comment="Risk profile this alert relates to",
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Alert type: drawdown | position_size | diversification | volatility | custom",
    )

    severity: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="medium",
        comment="Alert severity: low | medium | high | critical",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Alert title/summary",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed alert message",
    )

    # Trigger data
    trigger_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Value that triggered the alert",
    )

    threshold_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Threshold that was breached",
    )

    # Context data
    context_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Additional context data for the alert",
    )

    # Notification status
    email_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether email notification was sent",
    )

    sms_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether SMS notification was sent",
    )

    # Resolution
    is_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether this alert has been resolved",
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this alert was resolved",
    )

    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about alert resolution",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="risk_alerts")
    profile: Mapped["RiskProfile"] = relationship("RiskProfile", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<RiskAlert {self.alert_type} severity={self.severity} resolved={self.is_resolved}>"


class UserRiskMetrics(Base, TimestampMixin):
    """
    Real-time risk exposure tracking and monitoring data.

    Stores current risk metrics for portfolio monitoring and alerting.
    """

    __tablename__ = "user_risk_metrics"
    __table_args__ = (
        Index("ix_risk_metrics_user_id", "user_id"),
        Index("ix_risk_metrics_timestamp", "timestamp"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User these metrics belong to",
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Timestamp for these metrics",
    )

    # Portfolio risk metrics
    portfolio_value: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Current portfolio value",
    )

    portfolio_risk: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Current portfolio risk exposure",
    )

    daily_pnl: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Daily profit/loss",
    )

    daily_pnl_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Daily P&L percentage",
    )

    # Drawdown metrics
    current_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Current drawdown from peak",
    )

    max_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Maximum drawdown in period",
    )

    peak_value: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Peak portfolio value",
    )

    # Volatility metrics
    portfolio_volatility: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Portfolio volatility (annualized)",
    )

    sharpe_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Current Sharpe ratio",
    )

    # Position concentration
    largest_position_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Largest position as percentage of portfolio",
    )

    top_10_positions_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Top 10 positions as percentage of portfolio",
    )

    # Diversification metrics
    sector_diversification_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Sector diversification score (0-1, higher is better)",
    )

    stock_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of stocks in portfolio",
    )

    # Market condition metrics
    market_volatility: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Current market volatility",
    )

    vix_level: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Current VIX level",
    )

    # Risk limit status
    risk_limits_breached: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
        comment="List of breached risk limits",
    )

    # Additional metrics
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Additional risk metrics and context",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="risk_metrics")

    def __repr__(self) -> str:
        return f"<UserRiskMetrics user={self.user_id} risk={self.portfolio_risk:.3f} drawdown={self.current_drawdown:.3f}>"


class DrawdownLimit(Base, TimestampMixin, AuditMixin):
    """
    Maximum drawdown controls and recovery management.

    Defines drawdown limits and automatic recovery procedures.
    """

    __tablename__ = "drawdown_limit"
    __table_args__ = (
        Index("ix_drawdown_limit_user_id", "user_id"),
        Index("ix_drawdown_limit_is_active", "is_active"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this limit belongs to",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Limit name for identification",
    )

    # Drawdown settings
    max_drawdown_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Maximum drawdown percentage",
    )

    warning_threshold_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.5",  # 50% of max
        comment="Warning threshold as percentage of max drawdown",
    )

    # Recovery settings
    recovery_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether recovery is required before resuming trading",
    )

    recovery_target_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.8",  # 80% recovery
        comment="Recovery target as percentage of drawdown",
    )

    # Action settings
    action_on_breach: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="halt_trading",
        comment="Action on breach: halt_trading | reduce_positions | alert_only | custom",
    )

    gradual_recovery: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether to allow gradual position rebuilding",
    )

    max_recovery_position_size: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.5",  # 50% of normal size
        comment="Maximum position size during recovery",
    )

    # Status tracking
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this limit is active",
    )

    current_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Current drawdown percentage",
    )

    is_breached: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether this limit is currently breached",
    )

    breached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this limit was breached",
    )

    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When recovery was achieved",
    )

    # Usage tracking
    breach_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of times this limit has been breached",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="drawdown_limits")

    def __repr__(self) -> str:
        return f"<DrawdownLimit {self.name!r} max={self.max_drawdown_pct:.1%} breached={self.is_breached}>"


class DiversificationRule(Base, TimestampMixin, AuditMixin):
    """
    Portfolio diversification requirements and monitoring.

    Ensures portfolio meets diversification criteria for risk management.
    """

    __tablename__ = "diversification_rule"
    __table_args__ = (
        Index("ix_diversification_rule_user_id", "user_id"),
        Index("ix_diversification_rule_is_active", "is_active"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User this rule belongs to",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Rule name for identification",
    )

    # Diversification requirements
    min_sectors: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="5",
        comment="Minimum number of sectors required",
    )

    max_sector_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.25",  # 25%
        comment="Maximum weight per sector",
    )

    min_stocks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="10",
        comment="Minimum number of stocks required",
    )

    max_stock_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",  # 5%
        comment="Maximum weight per stock",
    )

    # Industry/country limits
    max_industry_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.15",  # 15%
        comment="Maximum weight per industry",
    )

    max_country_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.50",  # 50%
        comment="Maximum weight per country",
    )

    # Risk-based limits
    max_volatility_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.40",  # 40%
        comment="Maximum weight for high-volatility stocks",
    )

    volatility_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.30",  # 30%
        comment="Volatility threshold for high-volatility classification",
    )

    # Enforcement settings
    strict_enforcement: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether to strictly enforce limits (block trades)",
    )

    warning_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.8",  # 80%
        comment="Warning threshold as fraction of limit",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this rule is active",
    )

    # Current status
    is_compliant: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether portfolio currently meets diversification requirements",
    )

    compliance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="1.0",
        comment="Diversification compliance score (0-1, higher is better)",
    )

    last_checked: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Last time compliance was checked",
    )

    # Violation tracking
    violation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of times this rule has been violated",
    )

    last_violation: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this rule was violated",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="diversification_rules")

    def __repr__(self) -> str:
        return f"<DiversificationRule {self.name!r} compliant={self.is_compliant} score={self.compliance_score:.2f}>"