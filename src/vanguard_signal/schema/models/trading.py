"""
trading.py — Trading models for portfolio management, orders, positions, and risk tracking.

Tables
------
Portfolio      — User portfolios with account balances and settings
Order          — Trading orders (market, limit, stop) with execution tracking
Position       — Current positions with P&L calculations
RiskMetrics    — Portfolio risk analytics and limits

Uses the 'trading' schema in Postgres for financial data isolation.
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


class Portfolio(Base, TimestampMixin, AuditMixin):
    """
    User portfolio with account management and trading settings.

    Tracks account balance, margin, and trading permissions.
    """

    __tablename__ = "portfolio"
    __table_args__ = (
        Index("ix_portfolio_user_id", "user_id", unique=True),
        Index("ix_portfolio_is_active", "is_active"),
        {"schema": "trading"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who owns this portfolio",
    )
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Portfolio display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Portfolio description",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="USD",
        comment="Portfolio base currency (ISO 4217)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Active portfolio flag",
    )
    is_paper_trading: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Paper trading mode (no real money)",
    )

    # Account balances
    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Available cash balance",
    )
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Total portfolio value (cash + positions)",
    )

    # Risk settings
    max_position_size: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Maximum position size as % of portfolio (0.01 = 1%)",
    )
    max_daily_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Maximum daily loss as % of portfolio (0.02 = 2%)",
    )
    max_drawdown: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Maximum drawdown limit as % of portfolio",
    )

    # Trading permissions
    allow_margin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Allow margin trading",
    )
    allow_short_selling: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Allow short selling",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolio")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="portfolio")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio")
    risk_metrics: Mapped[list["RiskMetrics"]] = relationship("RiskMetrics", back_populates="portfolio")

    def __repr__(self) -> str:
        return f"<Portfolio {self.name!r} user={self.user_id} value={self.total_value}>"


class Order(Base, TimestampMixin, AuditMixin):
    """
    Trading order with execution tracking and status management.

    Supports market, limit, and stop orders with partial fills.
    """

    __tablename__ = "order"
    __table_args__ = (
        Index("ix_order_portfolio_id", "portfolio_id"),
        Index("ix_order_symbol", "symbol"),
        Index("ix_order_status", "status"),
        Index("ix_order_created_at", "created_at"),
        {"schema": "trading"},
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.portfolio.id", ondelete="CASCADE"),
        nullable=False,
        comment="Portfolio this order belongs to",
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
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Limit price (for limit/stop orders)",
    )
    stop_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Stop price (for stop orders)",
    )

    # Status and execution
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
        comment="Order status: pending | filled | partial | cancelled | rejected",
    )
    filled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
        server_default="0.00",
        comment="Quantity that has been filled",
    )
    average_fill_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Average price of filled portions",
    )

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="When order was submitted",
    )
    filled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order was completely filled",
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When order was cancelled",
    )

    # Additional metadata
    external_order_id: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment="Broker/external order identifier",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Order notes or comments",
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="orders")

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining unfilled quantity."""
        return self.quantity - self.filled_quantity

    @property
    def is_complete(self) -> bool:
        """Check if order is fully filled."""
        return self.filled_quantity >= self.quantity

    def __repr__(self) -> str:
        return f"<Order {self.symbol} {self.side} {self.quantity}@{self.price or 'market'} status={self.status}>"


class Position(Base, TimestampMixin, AuditMixin):
    """
    Current position with real-time P&L calculations.

    Tracks unrealized and realized P&L for portfolio valuation.
    """

    __tablename__ = "position"
    __table_args__ = (
        Index("ix_position_portfolio_symbol", "portfolio_id", "symbol", unique=True),
        Index("ix_position_portfolio_id", "portfolio_id"),
        Index("ix_position_symbol", "symbol"),
        {"schema": "trading"},
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.portfolio.id", ondelete="CASCADE"),
        nullable=False,
        comment="Portfolio this position belongs to",
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

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")

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
            self.last_updated = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Position {self.symbol} qty={self.quantity} avg_cost={self.average_cost} pnl={self.total_pnl}>"


class RiskMetrics(Base, TimestampMixin, AuditMixin):
    """
    Portfolio risk analytics and monitoring.

    Tracks various risk metrics for portfolio management and compliance.
    """

    __tablename__ = "risk_metrics"
    __table_args__ = (
        Index("ix_risk_metrics_portfolio_date", "portfolio_id", "calculated_at"),
        Index("ix_risk_metrics_portfolio_id", "portfolio_id"),
        {"schema": "trading"},
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.portfolio.id", ondelete="CASCADE"),
        nullable=False,
        comment="Portfolio these metrics belong to",
    )

    # Calculation timestamp
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="When these metrics were calculated",
    )

    # Risk metrics
    sharpe_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Sharpe ratio (risk-adjusted returns)",
    )
    sortino_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Sortino ratio (downside risk only)",
    )
    max_drawdown: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Maximum drawdown percentage",
    )
    value_at_risk: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Value at Risk (95% confidence)",
    )
    expected_shortfall: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Expected shortfall (CVaR)",
    )
    volatility: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Portfolio volatility (annualized)",
    )
    beta: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Portfolio beta vs market",
    )

    # Position concentrations
    largest_position_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Largest position as % of portfolio",
    )
    top_10_positions_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Top 10 positions as % of portfolio",
    )

    # Trading activity
    daily_turnover: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Daily turnover rate",
    )
    win_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Percentage of winning trades",
    )
    profit_factor: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Gross profit / gross loss ratio",
    )

    # Risk flags
    risk_warnings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="JSON object with risk warning flags",
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="risk_metrics")

    def __repr__(self) -> str:
        return f"<RiskMetrics portfolio={self.portfolio_id} sharpe={self.sharpe_ratio} max_dd={self.max_drawdown}>"


class MarketData(Base, TimestampMixin):
    """
    Cached market data for symbols.

    Stores historical price bars and quotes for fast access.
    """

    __tablename__ = "market_data"
    __table_args__ = (
        Index("ix_market_data_symbol_timestamp", "symbol", "timestamp"),
        Index("ix_market_data_symbol", "symbol"),
        Index("ix_market_data_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for market data entry",
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Stock symbol (e.g., AAPL, GOOGL)",
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of the data point",
    )

    data_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of data: bar, quote, trade",
    )

    # Bar data
    open_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Opening price for bar data",
    )
    high_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="High price for bar data",
    )
    low_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Low price for bar data",
    )
    close_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Closing price for bar data",
    )
    volume: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Trading volume",
    )

    # Quote data
    bid_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Bid price for quote data",
    )
    ask_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Ask price for quote data",
    )
    bid_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Bid size",
    )
    ask_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Ask size",
    )

    # Trade data
    trade_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Trade price",
    )
    trade_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Trade size",
    )

    # Metadata
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="alpaca",
        comment="Data source (alpaca, yahoo, etc.)",
    )

    timeframe: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Timeframe for bar data (1Min, 5Min, etc.)",
    )

    raw_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Raw data from source for debugging",
    )

    def __repr__(self) -> str:
        return f"<MarketData symbol={self.symbol} type={self.data_type} timestamp={self.timestamp}>"