"""
trading.py — Portfolio management, order execution, and risk monitoring.

Endpoints:
  GET    /api/trading/portfolios        — List user portfolios
  POST   /api/trading/portfolios        — Create new portfolio
  GET    /api/trading/portfolios/{id}   — Get portfolio details
  PUT    /api/trading/portfolios/{id}   — Update portfolio settings
  DELETE /api/trading/portfolios/{id}   — Delete portfolio

  GET    /api/trading/orders            — List orders with filtering
  POST   /api/trading/orders            — Submit new order
  GET    /api/trading/orders/{id}       — Get order details
  PUT    /api/trading/orders/{id}       — Update order (if pending)
  DELETE /api/trading/orders/{id}       — Cancel order (if pending)

  GET    /api/trading/positions         — List current positions
  GET    /api/trading/positions/{id}    — Get position details

  GET    /api/trading/risk              — Get portfolio risk metrics
  POST   /api/trading/risk/calculate    — Trigger risk calculation

  GET    /api/trading/market/price/{symbol}     — Get current market price
  GET    /api/trading/market/history/{symbol}   — Get historical market data
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vanguard_signal.api.deps import get_db, get_user_id
from vanguard_signal.simulation_service import SimulationEngine
from vanguard_signal.risk_management import RiskManagementService
from vanguard_signal.market_data import MarketDataService
from vanguard_signal.schema.models.trading import Order, Portfolio, Position, RiskMetrics


router = APIRouter(prefix="/api/trading", tags=["trading"])


# ── Pydantic Models ──────────────────────────────────────────────────────

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None, max_length=1000)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")
    is_paper_trading: bool = Field(True)
    max_position_size: Decimal | None = Field(None, ge=0, le=1)
    max_daily_loss: Decimal | None = Field(None, ge=0, le=1)
    max_drawdown: Decimal | None = Field(None, ge=0, le=1)
    allow_margin: bool = Field(False)
    allow_short_selling: bool = Field(False)


class PortfolioUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=1000)
    is_active: bool | None = None
    max_position_size: Decimal | None = Field(None, ge=0, le=1)
    max_daily_loss: Decimal | None = Field(None, ge=0, le=1)
    max_drawdown: Decimal | None = Field(None, ge=0, le=1)
    allow_margin: bool | None = None
    allow_short_selling: bool | None = None


class OrderCreate(BaseModel):
    portfolio_id: UUID
    symbol: str = Field(..., min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "stop", "stop_limit"]
    quantity: Decimal = Field(..., gt=0)
    price: Decimal | None = Field(None, gt=0)
    stop_price: Decimal | None = Field(None, gt=0)


class PortfolioRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    currency: str
    is_active: bool
    is_paper_trading: bool
    cash_balance: Decimal
    total_value: Decimal
    max_position_size: Decimal | None
    max_daily_loss: Decimal | None
    max_drawdown: Decimal | None
    allow_margin: bool
    allow_short_selling: bool
    created_at: str
    updated_at: str


class OrderRead(BaseModel):
    id: UUID
    portfolio_id: UUID
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    stop_price: Decimal | None
    status: str
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    submitted_at: str
    filled_at: str | None
    cancelled_at: str | None
    external_order_id: str | None
    notes: str | None


class PositionRead(BaseModel):
    id: UUID
    portfolio_id: UUID
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal | None
    market_value: Decimal | None
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    opened_at: str
    last_updated: str


class RiskMetricsRead(BaseModel):
    id: UUID
    portfolio_id: UUID
    calculated_at: str
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown: float | None
    value_at_risk: float | None
    expected_shortfall: float | None
    volatility: float | None
    beta: float | None
    largest_position_pct: float | None
    top_10_positions_pct: float | None
    daily_turnover: float | None
    win_rate: float | None
    profit_factor: float | None
    risk_warnings: dict


# ── Portfolio Endpoints ──────────────────────────────────────────────────

@router.get("/portfolios", response_model=list[PortfolioRead])
async def list_portfolios(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioRead]:
    """List all portfolios for the current user."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at.desc())
    )
    portfolios = result.scalars().all()

    return [
        PortfolioRead(
            id=p.id,
            name=p.name,
            description=p.description,
            currency=p.currency,
            is_active=p.is_active,
            is_paper_trading=p.is_paper_trading,
            cash_balance=p.cash_balance,
            total_value=p.total_value,
            max_position_size=p.max_position_size,
            max_daily_loss=p.max_daily_loss,
            max_drawdown=p.max_drawdown,
            allow_margin=p.allow_margin,
            allow_short_selling=p.allow_short_selling,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in portfolios
    ]


@router.post("/portfolios", response_model=PortfolioRead)
async def create_portfolio(
    data: PortfolioCreate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRead:
    """Create a new portfolio for the current user."""
    # Check if user already has a portfolio (for now, limit to one per user)
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    existing = result.first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already has a portfolio. Multiple portfolios not yet supported."
        )

    portfolio = Portfolio(
        user_id=user_id,
        name=data.name,
        description=data.description,
        currency=data.currency,
        is_paper_trading=data.is_paper_trading,
        max_position_size=data.max_position_size,
        max_daily_loss=data.max_daily_loss,
        max_drawdown=data.max_drawdown,
        allow_margin=data.allow_margin,
        allow_short_selling=data.allow_short_selling,
    )

    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)

    return PortfolioRead(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        currency=portfolio.currency,
        is_active=portfolio.is_active,
        is_paper_trading=portfolio.is_paper_trading,
        cash_balance=portfolio.cash_balance,
        total_value=portfolio.total_value,
        max_position_size=portfolio.max_position_size,
        max_daily_loss=portfolio.max_daily_loss,
        max_drawdown=portfolio.max_drawdown,
        allow_margin=portfolio.allow_margin,
        allow_short_selling=portfolio.allow_short_selling,
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioRead)
async def get_portfolio(
    portfolio_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRead:
    """Get details of a specific portfolio."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return PortfolioRead(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        currency=portfolio.currency,
        is_active=portfolio.is_active,
        is_paper_trading=portfolio.is_paper_trading,
        cash_balance=portfolio.cash_balance,
        total_value=portfolio.total_value,
        max_position_size=portfolio.max_position_size,
        max_daily_loss=portfolio.max_daily_loss,
        max_drawdown=portfolio.max_drawdown,
        allow_margin=portfolio.allow_margin,
        allow_short_selling=portfolio.allow_short_selling,
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


@router.put("/portfolios/{portfolio_id}", response_model=PortfolioRead)
async def update_portfolio(
    portfolio_id: UUID,
    data: PortfolioUpdate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRead:
    """Update portfolio settings."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Update fields
    for field, value in data.model_dump(exclude_unset=True).items():
        if hasattr(portfolio, field):
            setattr(portfolio, field, value)

    await db.commit()
    await db.refresh(portfolio)

    return PortfolioRead(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        currency=portfolio.currency,
        is_active=portfolio.is_active,
        is_paper_trading=portfolio.is_paper_trading,
        cash_balance=portfolio.cash_balance,
        total_value=portfolio.total_value,
        max_position_size=portfolio.max_position_size,
        max_daily_loss=portfolio.max_daily_loss,
        max_drawdown=portfolio.max_drawdown,
        allow_margin=portfolio.allow_margin,
        allow_short_selling=portfolio.allow_short_selling,
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


@router.get("/portfolios/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: UUID,
    period_days: int = Query(30, ge=1, le=365),
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get portfolio performance metrics."""
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trading_service = TradingService(db)
    performance = await trading_service.calculate_portfolio_performance(portfolio_id, period_days)

    if "error" in performance:
        raise HTTPException(status_code=500, detail=performance["error"])

    return performance


@router.post("/portfolios/{portfolio_id}/rebalance")
async def rebalance_portfolio(
    portfolio_id: UUID,
    target_allocations: dict[str, float],
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Calculate rebalancing trades for portfolio."""
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trading_service = TradingService(db)
    rebalance_result = await trading_service.rebalance_portfolio(portfolio_id, target_allocations)

    if "error" in rebalance_result:
        raise HTTPException(status_code=500, detail=rebalance_result["error"])

    return rebalance_result


@router.get("/portfolios/{portfolio_id}/alerts")
async def get_portfolio_alerts(
    portfolio_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get portfolio alerts and risk warnings."""
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trading_service = TradingService(db)
    alerts = await trading_service.check_portfolio_alerts(portfolio_id)

    if "error" in alerts:
        raise HTTPException(status_code=500, detail=alerts["error"])

    return alerts


# ── Order Endpoints ──────────────────────────────────────────────────────

@router.get("/orders", response_model=list[OrderRead])
async def list_orders(
    portfolio_id: UUID | None = Query(None),
    status: str | None = Query(None),
    symbol: str | None = Query(None),
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[OrderRead]:
    """List orders with optional filtering."""
    query = select(Order).join(Portfolio).where(Portfolio.user_id == user_id)

    if portfolio_id:
        query = query.where(Order.portfolio_id == portfolio_id)
    if status:
        query = query.where(Order.status == status)
    if symbol:
        query = query.where(Order.symbol == symbol)

    result = await db.execute(query.order_by(Order.created_at.desc()))
    orders = result.scalars().all()

    return [
        OrderRead(
            id=o.id,
            portfolio_id=o.portfolio_id,
            symbol=o.symbol,
            side=o.side,
            order_type=o.order_type,
            quantity=o.quantity,
            price=o.price,
            stop_price=o.stop_price,
            status=o.status,
            filled_quantity=o.filled_quantity,
            average_fill_price=o.average_fill_price,
            submitted_at=o.submitted_at.isoformat(),
            filled_at=o.filled_at.isoformat() if o.filled_at else None,
            cancelled_at=o.cancelled_at.isoformat() if o.cancelled_at else None,
            external_order_id=o.external_order_id,
            notes=o.notes,
        )
        for o in orders
    ]


@router.post("/orders", response_model=OrderRead)
async def create_order(
    data: OrderCreate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    """Submit a new order (paper trading only for now)."""
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == data.portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if not portfolio.is_paper_trading:
        raise HTTPException(
            status_code=400,
            detail="Live trading not yet implemented. Use paper trading only."
        )

    # Basic validation
    if data.order_type in ["limit", "stop_limit"] and not data.price:
        raise HTTPException(status_code=400, detail="Price required for limit orders")

    if data.order_type in ["stop", "stop_limit"] and not data.stop_price:
        raise HTTPException(status_code=400, detail="Stop price required for stop orders")

    # Create order (initially pending)
    order = Order(
        portfolio_id=data.portfolio_id,
        symbol=data.symbol,
        side=data.side,
        order_type=data.order_type,
        quantity=data.quantity,
        price=data.price,
        stop_price=data.stop_price,
        status="pending",  # Start as pending
    )

    db.add(order)
    await db.commit()  # Commit to get the order ID
    await db.refresh(order)

    # Execute the order using TradingService
    trading_service = TradingService(db)
    execution_result = await trading_service.execute_order(order)

    # Refresh order to get updated status
    await db.refresh(order)

    if not execution_result["success"]:
        # If execution failed, return the error
        raise HTTPException(
            status_code=400,
            detail=f"Order execution failed: {execution_result.get('error', 'Unknown error')}"
        )

    return OrderRead(
        id=order.id,
        portfolio_id=order.portfolio_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        price=order.price,
        stop_price=order.stop_price,
        status=order.status,
        filled_quantity=order.filled_quantity,
        average_fill_price=order.average_fill_price,
        submitted_at=order.submitted_at.isoformat(),
        filled_at=order.filled_at.isoformat() if order.filled_at else None,
        cancelled_at=order.cancelled_at.isoformat() if order.cancelled_at else None,
        external_order_id=order.external_order_id,
        notes=order.notes,
    )


# ── Position Endpoints ───────────────────────────────────────────────────

@router.get("/positions", response_model=list[PositionRead])
async def list_positions(
    portfolio_id: UUID | None = Query(None),
    symbol: str | None = Query(None),
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[PositionRead]:
    """List current positions."""
    query = select(Position).join(Portfolio).where(Portfolio.user_id == user_id)

    if portfolio_id:
        query = query.where(Position.portfolio_id == portfolio_id)
    if symbol:
        query = query.where(Position.symbol == symbol)

    result = await db.execute(query.order_by(Position.opened_at.desc()))
    positions = result.scalars().all()

    return [
        PositionRead(
            id=p.id,
            portfolio_id=p.portfolio_id,
            symbol=p.symbol,
            quantity=p.quantity,
            average_cost=p.average_cost,
            current_price=p.current_price,
            market_value=p.market_value,
            unrealized_pnl=p.unrealized_pnl,
            realized_pnl=p.realized_pnl,
            opened_at=p.opened_at.isoformat(),
            last_updated=p.last_updated.isoformat(),
        )
        for p in positions
    ]


# ── Risk Metrics Endpoints ───────────────────────────────────────────────

@router.get("/risk", response_model=list[RiskMetricsRead])
async def get_risk_metrics(
    portfolio_id: UUID | None = Query(None),
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[RiskMetricsRead]:
    """Get latest risk metrics for portfolios."""
    query = select(RiskMetrics).join(Portfolio).where(Portfolio.user_id == user_id)

    if portfolio_id:
        query = query.where(RiskMetrics.portfolio_id == portfolio_id)

    result = await db.execute(
        query.order_by(RiskMetrics.calculated_at.desc()).limit(10)
    )
    metrics = result.scalars().all()

    return [
        RiskMetricsRead(
            id=m.id,
            portfolio_id=m.portfolio_id,
            calculated_at=m.calculated_at.isoformat(),
            sharpe_ratio=m.sharpe_ratio,
            sortino_ratio=m.sortino_ratio,
            max_drawdown=m.max_drawdown,
            value_at_risk=m.value_at_risk,
            expected_shortfall=m.expected_shortfall,
            volatility=m.volatility,
            beta=m.beta,
            largest_position_pct=m.largest_position_pct,
            top_10_positions_pct=m.top_10_positions_pct,
            daily_turnover=m.daily_turnover,
            win_rate=m.win_rate,
            profit_factor=m.profit_factor,
            risk_warnings=m.risk_warnings,
        )
        for m in metrics
    ]


@router.post("/risk/calculate")
async def calculate_risk_metrics(
    portfolio_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Calculate and store risk metrics for a portfolio."""
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trading_service = TradingService(db)
    metrics = await trading_service.calculate_risk_metrics(portfolio_id)

    if "error" in metrics:
        raise HTTPException(status_code=500, detail=metrics["error"])

    return metrics


# ── Market Data Endpoints ───────────────────────────────────────────────

@router.get("/market/price/{symbol}")
async def get_market_price(symbol: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get current market price for a symbol."""
    market_data = MarketDataService(db)
    price = await market_data.get_current_price(symbol.upper())

    if price is None:
        raise HTTPException(status_code=404, detail=f"Price not available for {symbol}")

    return {
        "symbol": symbol.upper(),
        "price": price,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/market/history/{symbol}")
async def get_market_history(
    symbol: str,
    timeframe: str = Query("1Min", description="Timeframe: 1Min, 5Min, 15Min, 1Hour, 1Day"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get historical market data for a symbol."""
    from alpaca.data.timeframe import TimeFrame

    timeframe_map = {
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrame.Minute),
        "15Min": TimeFrame(15, TimeFrame.Minute),
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
    }

    tf = timeframe_map.get(timeframe, TimeFrame.Minute)

    market_data = MarketDataService(db)
    bars = await market_data.get_historical_bars(symbol.upper(), tf, limit=limit)

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bars": [
            {
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars
        ]
    }


# ── Simulation Endpoints ─────────────────────────────────────────────────

class SimulationCreate(BaseModel):
    """Request model for creating a simulation session."""
    name: str = Field(..., description="Name of the simulation")
    description: str = Field("", description="Optional description")
    initial_balance: Decimal = Field(100000, gt=0, description="Starting balance in USD")
    strategy_config: dict = Field(default_factory=dict, description="Strategy configuration")
    market_conditions: dict = Field(default_factory=dict, description="Market condition overrides")


class SimulationOrderCreate(BaseModel):
    """Request model for placing simulation orders."""
    symbol: str = Field(..., description="Stock symbol")
    side: Literal["buy", "sell"] = Field(..., description="Order side")
    quantity: int = Field(..., gt=0, description="Number of shares")
    order_type: Literal["market", "limit"] = Field("market", description="Order type")
    price: Decimal | None = Field(None, description="Limit price (required for limit orders)")


@router.post("/simulations")
async def create_simulation(
    request: SimulationCreate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Create a new paper trading simulation session."""
    engine = SimulationEngine(db)
    session_id = await engine.create_session(
        user_id=user_id,
        name=request.name,
        description=request.description,
        initial_balance=request.initial_balance,
        strategy_config=request.strategy_config,
        market_conditions=request.market_conditions
    )

    return {"session_id": session_id, "status": "created"}


@router.get("/simulations")
async def list_simulations(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """List all simulation sessions for the user."""
    engine = SimulationEngine(db)
    sessions = await engine.list_sessions(user_id)

    return [
        {
            "id": str(session.id),
            "name": session.name,
            "description": session.description,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "initial_balance": session.initial_balance,
            "current_balance": session.current_balance,
            "total_return": session.total_return,
            "total_trades": session.total_trades,
        }
        for session in sessions
    ]


@router.get("/simulations/{session_id}")
async def get_simulation(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get detailed information about a simulation session."""
    engine = SimulationEngine(db)
    session = await engine.get_session(session_id, user_id)

    if not session:
        raise HTTPException(status_code=404, detail="Simulation session not found")

    return {
        "id": str(session.id),
        "name": session.name,
        "description": session.description,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "initial_balance": session.initial_balance,
        "current_balance": session.current_balance,
        "total_return": session.total_return,
        "total_trades": session.total_trades,
        "strategy_config": session.strategy_config,
        "market_conditions": session.market_conditions,
    }


@router.post("/simulations/{session_id}/start")
async def start_simulation(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Start a simulation session."""
    engine = SimulationEngine(db)
    success = await engine.start_session(session_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Simulation session not found or already running")

    return {"status": "started"}


@router.post("/simulations/{session_id}/stop")
async def stop_simulation(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Stop a simulation session."""
    engine = SimulationEngine(db)
    success = await engine.stop_session(session_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Simulation session not found or not running")

    return {"status": "stopped"}


@router.post("/simulations/{session_id}/orders")
async def place_simulation_order(
    session_id: UUID,
    request: SimulationOrderCreate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Place an order in a simulation session."""
    engine = SimulationEngine(db)
    order_id = await engine.place_order(
        session_id=session_id,
        user_id=user_id,
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        price=request.price
    )

    if not order_id:
        raise HTTPException(status_code=400, detail="Failed to place order")

    return {"order_id": order_id, "status": "placed"}


@router.get("/simulations/{session_id}/orders")
async def get_simulation_orders(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """Get all orders for a simulation session."""
    engine = SimulationEngine(db)
    orders = await engine.get_session_orders(session_id, user_id)

    return [
        {
            "id": str(order.id),
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "price": order.price,
            "status": order.status,
            "executed_at": order.executed_at.isoformat() if order.executed_at else None,
            "execution_price": order.execution_price,
        }
        for order in orders
    ]


@router.get("/simulations/{session_id}/positions")
async def get_simulation_positions(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """Get current positions for a simulation session."""
    engine = SimulationEngine(db)
    positions = await engine.get_session_positions(session_id, user_id)

    return [
        {
            "id": str(position.id),
            "symbol": position.symbol,
            "quantity": position.quantity,
            "average_cost": position.average_cost,
            "current_price": position.current_price,
            "market_value": position.market_value,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_percent": position.unrealized_pnl_percent,
        }
        for position in positions
    ]


@router.get("/simulations/{session_id}/metrics")
async def get_simulation_metrics(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get performance metrics for a simulation session."""
    engine = SimulationEngine(db)
    metrics = await engine.get_session_metrics(session_id, user_id)

    if not metrics:
        raise HTTPException(status_code=404, detail="Simulation session not found")

    return {
        "total_return": metrics.total_return,
        "total_return_percent": metrics.total_return_percent,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown": metrics.max_drawdown,
        "win_rate": metrics.win_rate,
        "total_trades": metrics.total_trades,
        "avg_trade_return": metrics.avg_trade_return,
        "largest_win": metrics.largest_win,
        "largest_loss": metrics.largest_loss,
    }


@router.delete("/simulations/{session_id}")
async def delete_simulation(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a simulation session."""
    engine = SimulationEngine(db)
    success = await engine.delete_session(session_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Simulation session not found")

    return {"status": "deleted"}


# ── Risk Management Endpoints ────────────────────────────────────────────

class RiskProfileUpdate(BaseModel):
    """Request model for updating risk profile."""
    risk_tolerance: Literal["conservative", "moderate", "aggressive"] = Field(default="moderate")
    max_portfolio_risk: float = Field(default=0.02, ge=0.001, le=0.10)
    max_single_position_risk: float = Field(default=0.01, ge=0.001, le=0.05)
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.20)
    max_drawdown: float = Field(default=0.10, ge=0.05, le=0.50)
    position_sizing_method: Literal["fixed_percentage", "kelly_criterion", "equal_risk"] = Field(default="fixed_percentage")
    base_position_size: float = Field(default=0.02, ge=0.001, le=0.10)
    kelly_fraction: float = Field(default=0.5, ge=0.1, le=1.0)
    max_sector_exposure: float = Field(default=0.25, ge=0.05, le=0.50)
    max_single_stock_exposure: float = Field(default=0.05, ge=0.01, le=0.20)
    min_diversification_stocks: int = Field(default=5, ge=1, le=50)
    use_stop_loss: bool = Field(default=True)
    default_stop_loss_pct: float = Field(default=0.05, ge=0.01, le=0.30)
    trailing_stop_enabled: bool = Field(default=False)
    circuit_breaker_enabled: bool = Field(default=True)
    volatility_threshold: float = Field(default=0.03, ge=0.01, le=0.20)
    market_drop_threshold: float = Field(default=0.05, ge=0.01, le=0.20)
    email_alerts_enabled: bool = Field(default=True)
    sms_alerts_enabled: bool = Field(default=False)


class PositionSizeRequest(BaseModel):
    """Request model for position size calculation."""
    symbol: str = Field(..., description="Stock symbol")
    entry_price: Decimal = Field(..., gt=0, description="Entry price")
    stop_loss_price: Optional[Decimal] = Field(None, description="Stop loss price")
    win_probability: Optional[float] = Field(None, ge=0, le=1, description="Win probability for Kelly")
    win_loss_ratio: Optional[float] = Field(None, gt=0, description="Win/loss ratio for Kelly")


@router.get("/risk/profile")
async def get_risk_profile(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get user's risk profile."""
    risk_service = RiskManagementService(db)
    profile = await risk_service.get_or_create_risk_profile(user_id)

    return {
        "id": str(profile.id),
        "risk_tolerance": profile.risk_tolerance,
        "max_portfolio_risk": profile.max_portfolio_risk,
        "max_single_position_risk": profile.max_single_position_risk,
        "max_daily_loss": profile.max_daily_loss,
        "max_drawdown": profile.max_drawdown,
        "position_sizing_method": profile.position_sizing_method,
        "base_position_size": profile.base_position_size,
        "kelly_fraction": profile.kelly_fraction,
        "max_sector_exposure": profile.max_sector_exposure,
        "max_single_stock_exposure": profile.max_single_stock_exposure,
        "min_diversification_stocks": profile.min_diversification_stocks,
        "use_stop_loss": profile.use_stop_loss,
        "default_stop_loss_pct": profile.default_stop_loss_pct,
        "trailing_stop_enabled": profile.trailing_stop_enabled,
        "circuit_breaker_enabled": profile.circuit_breaker_enabled,
        "volatility_threshold": profile.volatility_threshold,
        "market_drop_threshold": profile.market_drop_threshold,
        "email_alerts_enabled": profile.email_alerts_enabled,
        "sms_alerts_enabled": profile.sms_alerts_enabled,
        "is_active": profile.is_active,
    }


@router.put("/risk/profile")
async def update_risk_profile(
    request: RiskProfileUpdate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update user's risk profile."""
    risk_service = RiskManagementService(db)
    profile = await risk_service.get_or_create_risk_profile(user_id)

    # Update profile fields
    for field, value in request.model_dump().items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return {"status": "updated", "profile_id": str(profile.id)}


@router.post("/risk/position-size")
async def calculate_position_size(
    request: PositionSizeRequest,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Calculate recommended position size."""
    risk_service = RiskManagementService(db)
    result = await risk_service.calculate_position_size(
        user_id=user_id,
        symbol=request.symbol,
        entry_price=request.entry_price,
        stop_loss_price=request.stop_loss_price,
        win_probability=request.win_probability,
        win_loss_ratio=request.win_loss_ratio,
    )

    return result


@router.get("/risk/metrics")
async def get_risk_metrics(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get current risk metrics."""
    risk_service = RiskManagementService(db)
    metrics = await risk_service.update_risk_metrics(user_id)

    return {
        "portfolio_value": float(metrics.portfolio_value),
        "portfolio_risk": metrics.portfolio_risk,
        "daily_pnl": float(metrics.daily_pnl),
        "daily_pnl_percent": metrics.daily_pnl_percent,
        "current_drawdown": metrics.current_drawdown,
        "max_drawdown": metrics.max_drawdown,
        "portfolio_volatility": metrics.portfolio_volatility,
        "sharpe_ratio": metrics.sharpe_ratio,
        "largest_position_pct": metrics.largest_position_pct,
        "stock_count": metrics.stock_count,
        "market_volatility": metrics.market_volatility,
        "vix_level": metrics.vix_level,
        "risk_limits_breached": metrics.risk_limits_breached,
        "timestamp": metrics.timestamp.isoformat(),
    }


@router.get("/risk/stops")
async def check_stop_triggers(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """Check for stop-loss triggers."""
    risk_service = RiskManagementService(db)
    triggers = await risk_service.check_stop_loss_triggers(user_id)

    return triggers


@router.get("/risk/circuit-breakers")
async def check_circuit_breakers(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """Check circuit breaker conditions."""
    risk_service = RiskManagementService(db)
    breakers = await risk_service.check_circuit_breakers(user_id)

    return breakers


@router.get("/risk/alerts")
async def get_risk_alerts(
    resolved: bool = Query(False, description="Include resolved alerts"),
    limit: int = Query(50, ge=1, le=100),
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """Get risk alerts."""
    from vanguard_signal.schema.models.risk_management import RiskAlert

    result = await db.execute(
        select(RiskAlert)
        .where(RiskAlert.user_id == user_id)
        .where(RiskAlert.is_resolved == resolved)
        .order_by(RiskAlert.created_at.desc())
        .limit(limit)
    )
    alerts = result.scalars().all()

    return [
        {
            "id": str(alert.id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "trigger_value": alert.trigger_value,
            "threshold_value": alert.threshold_value,
            "is_resolved": alert.is_resolved,
            "created_at": alert.created_at.isoformat(),
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }
        for alert in alerts
    ]


@router.post("/risk/check-limits")
async def check_risk_limits(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Check all risk limits and return any violations."""
    risk_service = RiskManagementService(db)
    alerts = await risk_service.check_all_risk_limits(user_id)

    return {
        "alerts_created": len(alerts),
        "alerts": [
            {
                "id": str(alert.id),
                "type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
            }
            for alert in alerts
        ],
    }


@router.post("/risk/alerts/{alert_id}/resolve")
async def resolve_risk_alert(
    alert_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Resolve a risk alert."""
    from vanguard_signal.schema.models.risk_management import RiskAlert

    result = await db.execute(
        select(RiskAlert)
        .where(
            and_(
                RiskAlert.id == alert_id,
                RiskAlert.user_id == user_id
            )
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "resolved"}