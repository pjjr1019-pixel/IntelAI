"""
simulation.py — Paper trading simulation models for risk-free strategy testing.

Tables
------
SimulationSession    — Simulation run configuration and metadata
SimulationOrder      — Simulated orders with execution details
SimulationPosition   — Simulated positions with P&L tracking
SimulationResult     — Performance metrics and analytics for simulations
MarketCondition      — Market regime and volatility conditions for testing
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vanguard_signal.schema.base import Base, AuditMixin, TimestampMixin


class SimulationSession(Base, TimestampMixin, AuditMixin):
    """
    Paper trading simulation session configuration and metadata.

    Defines the parameters for a complete simulation run including
    market conditions, capital allocation, and testing scenarios.
    """

    __tablename__ = "simulation_session"
    __table_args__ = (
        Index("ix_simulation_session_user_id", "user_id"),
        Index("ix_simulation_session_status", "status"),
        Index("ix_simulation_session_created_at", "created_at"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who owns this simulation",
    )

    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Simulation session name",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Simulation description and objectives",
    )

    # Simulation configuration
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
        comment="Simulation status: pending | running | completed | failed",
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Simulation start date",
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Simulation end date",
    )

    # Capital and risk settings
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Starting capital for simulation",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="USD",
        comment="Simulation currency",
    )

    # Market conditions
    market_regime: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="normal",
        comment="Market regime: bull | bear | sideways | volatile | normal",
    )

    volatility_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="moderate",
        comment="Volatility level: low | moderate | high | extreme",
    )

    # Simulation parameters
    commission_per_trade: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=8),
        nullable=False,
        server_default="0.001",  # 0.1%
        comment="Commission per trade as decimal (0.001 = 0.1%)",
    )

    slippage_model: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="fixed",
        comment="Slippage model: none | fixed | percentage | volume_based",
    )

    slippage_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=8),
        nullable=False,
        server_default="0.0005",  # 0.05%
        comment="Slippage amount (interpretation depends on model)",
    )

    # Risk management
    max_position_size: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Maximum position size as % of capital",
    )

    max_daily_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Maximum daily loss as % of capital",
    )

    # Strategy configuration
    strategy_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Strategy-specific configuration parameters",
    )

    # Results summary (populated after completion)
    final_value: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Final portfolio value at simulation end",
    )

    total_return: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Total return percentage",
    )

    sharpe_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Risk-adjusted return metric",
    )

    max_drawdown: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Maximum drawdown percentage",
    )

    win_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Percentage of winning trades",
    )

    total_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Total number of trades executed",
    )

    # Metadata
    random_seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Random seed for reproducible simulations",
    )

    execution_time_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total execution time in seconds",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="simulation_sessions")
    orders: Mapped[list["SimulationOrder"]] = relationship("SimulationOrder", back_populates="session")
    positions: Mapped[list["SimulationPosition"]] = relationship("SimulationPosition", back_populates="session")
    results: Mapped[list["SimulationResult"]] = relationship("SimulationResult", back_populates="session")

    def __repr__(self) -> str:
        return f"<SimulationSession {self.name!r} status={self.status} return={self.total_return}>"


class SimulationOrder(Base, TimestampMixin, AuditMixin):
    """
    Simulated order with execution details and market impact.

    Tracks order execution in paper trading with realistic slippage and commissions.
    """

    __tablename__ = "simulation_order"
    __table_args__ = (
        Index("ix_simulation_order_session_id", "session_id"),
        Index("ix_simulation_order_symbol", "symbol"),
        Index("ix_simulation_order_status", "status"),
        {"schema": "trading"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.simulation_session.id", ondelete="CASCADE"),
        nullable=False,
        comment="Simulation session this order belongs to",
    )

    # Order details
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Trading symbol/ticker",
    )

    side: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        comment="Order side: buy | sell",
    )

    order_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Order type: market | limit | stop",
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Order quantity",
    )

    # Pricing
    requested_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Requested price (for limit/stop orders)",
    )

    executed_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Actual execution price after slippage",
    )

    slippage_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Slippage applied to this order",
    )

    commission: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Commission charged for this trade",
    )

    # Status and timing
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
        comment="Order status: pending | filled | cancelled | rejected",
    )

    order_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the order was placed in simulation time",
    )

    execution_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the order was executed",
    )

    # Market conditions at execution
    market_price_at_order: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Market price when order was placed",
    )

    market_volatility: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Market volatility at execution time",
    )

    # Additional metadata
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Execution notes or special conditions",
    )

    # Relationships
    session: Mapped["SimulationSession"] = relationship("SimulationSession", back_populates="orders")

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including commission."""
        if self.executed_price and self.quantity:
            return (self.executed_price * self.quantity) + self.commission
        return Decimal("0")

    def __repr__(self) -> str:
        return f"<SimulationOrder {self.symbol} {self.side} {self.quantity}@{self.executed_price}>"


class SimulationPosition(Base, TimestampMixin, AuditMixin):
    """
    Simulated position with P&L tracking and risk metrics.

    Tracks position lifecycle in paper trading with detailed performance analytics.
    """

    __tablename__ = "simulation_position"
    __table_args__ = (
        Index("ix_simulation_position_session_symbol", "session_id", "symbol", unique=True),
        Index("ix_simulation_position_session_id", "session_id"),
        {"schema": "trading"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.simulation_session.id", ondelete="CASCADE"),
        nullable=False,
        comment="Simulation session this position belongs to",
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Trading symbol/ticker",
    )

    # Position details
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Current position quantity (positive = long, negative = short)",
    )

    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Average cost basis per unit",
    )

    # Current market data
    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Current market price",
    )

    market_value: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Current market value (quantity * current_price)",
    )

    # P&L calculations
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Unrealized profit/loss",
    )

    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Realized profit/loss from closed portions",
    )

    # Position metadata
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="When position was first opened",
    )

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Last position update timestamp",
    )

    # Risk metrics
    peak_value: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Peak market value of position",
    )

    max_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Maximum drawdown percentage from peak",
    )

    holding_period_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Days position has been held",
    )

    # Relationships
    session: Mapped["SimulationSession"] = relationship("SimulationSession", back_populates="positions")

    @property
    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.quantity < 0

    @property
    def total_pnl(self) -> Decimal:
        """Calculate total P&L (unrealized + realized)."""
        return self.unrealized_pnl + self.realized_pnl

    def update_pnl(self, current_price: Decimal) -> None:
        """Update unrealized P&L based on current price."""
        if current_price is not None:
            self.current_price = current_price
            self.market_value = self.quantity * current_price
            self.unrealized_pnl = (current_price - self.average_cost) * self.quantity

            # Update drawdown tracking
            if self.market_value and self.market_value > self.peak_value:
                self.peak_value = self.market_value

            if self.peak_value > 0 and self.market_value:
                current_drawdown = ((self.peak_value - self.market_value) / self.peak_value) * 100
                self.max_drawdown = max(self.max_drawdown, current_drawdown)

            self.last_updated = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<SimulationPosition {self.symbol} qty={self.quantity} pnl={self.total_pnl}>"


class SimulationResult(Base, TimestampMixin, AuditMixin):
    """
    Detailed performance analytics for simulation sessions.

    Stores time-series performance data, trade analysis, and risk metrics.
    """

    __tablename__ = "simulation_result"
    __table_args__ = (
        Index("ix_simulation_result_session_timestamp", "session_id", "timestamp"),
        Index("ix_simulation_result_session_id", "session_id"),
        {"schema": "trading"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.simulation_session.id", ondelete="CASCADE"),
        nullable=False,
        comment="Simulation session these results belong to",
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp for this result snapshot",
    )

    # Portfolio state
    portfolio_value: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Total portfolio value at this timestamp",
    )

    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        comment="Cash balance at this timestamp",
    )

    # Performance metrics
    cumulative_return: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Cumulative return percentage from start",
    )

    daily_return: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Daily return percentage",
    )

    # Risk metrics
    volatility: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Rolling volatility (annualized)",
    )

    sharpe_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Rolling Sharpe ratio",
    )

    max_drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
        comment="Maximum drawdown from start to this point",
    )

    # Trading activity
    total_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Cumulative trades up to this point",
    )

    winning_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Cumulative winning trades",
    )

    losing_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Cumulative losing trades",
    )

    # Market conditions
    vix_level: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="VIX level (volatility index) at this time",
    )

    market_regime: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Detected market regime at this time",
    )

    # Additional analytics
    result_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Additional analytics and custom metrics",
    )

    # Relationships
    session: Mapped["SimulationSession"] = relationship("SimulationSession", back_populates="results")

    @property
    def win_rate(self) -> float:
        """Calculate win rate up to this point."""
        total_closed = self.winning_trades + self.losing_trades
        return (self.winning_trades / total_closed * 100) if total_closed > 0 else 0.0

    def __repr__(self) -> str:
        return f"<SimulationResult session={self.session_id} value={self.portfolio_value} return={self.cumulative_return}>"


class MarketCondition(Base, TimestampMixin):
    """
    Market regime and volatility conditions for simulation testing.

    Defines different market environments to test strategies against.
    """

    __tablename__ = "market_condition"
    __table_args__ = (
        Index("ix_market_condition_regime", "regime"),
        Index("ix_market_condition_volatility", "volatility_level"),
        {"schema": "trading"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for market condition",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name for this condition",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of market conditions",
    )

    # Market regime classification
    regime: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Market regime: bull | bear | sideways | volatile | crash | bubble",
    )

    volatility_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Volatility level: low | moderate | high | extreme",
    )

    # Statistical properties
    avg_daily_return: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Average daily return percentage",
    )

    volatility: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Annualized volatility percentage",
    )

    # Market microstructure
    bid_ask_spread: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.05",
        comment="Typical bid-ask spread percentage",
    )

    market_depth: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="normal",
        comment="Market depth: thin | normal | deep",
    )

    # Historical context
    based_on_period: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Historical period this condition is based on (e.g., '2008-crisis', '2020-pandemic')",
    )

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="How many times this condition has been used in simulations",
    )

    # Configuration
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Additional configuration parameters",
    )

    def __repr__(self) -> str:
        return f"<MarketCondition {self.name!r} regime={self.regime} vol={self.volatility_level}>"