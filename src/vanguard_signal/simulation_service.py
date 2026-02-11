"""
simulation_service.py — Paper trading simulation engine for risk-free strategy testing.

Provides realistic market simulation with slippage, commissions, and various market conditions.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vanguard_signal.schema.models.simulation import (
    SimulationSession,
    SimulationOrder,
    SimulationPosition,
    SimulationResult,
    MarketCondition,
)
from vanguard_signal.schema.models import User
from vanguard_signal.market_data import MarketDataService

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Realistic market simulation engine for paper trading."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data = MarketDataService(db)
        self.random_seed: Optional[int] = None

    def set_random_seed(self, seed: int) -> None:
        """Set random seed for reproducible simulations."""
        self.random_seed = seed
        random.seed(seed)
        np.random.seed(seed)

    async def create_session(
        self,
        user_id: UUID,
        name: str,
        description: str = "",
        initial_balance: Decimal = Decimal("100000"),
        strategy_config: dict = None,
        market_conditions: dict = None
    ) -> UUID:
        """Create a new simulation session."""
        if strategy_config is None:
            strategy_config = {}
        if market_conditions is None:
            market_conditions = {}

        # Set default market conditions
        market_regime = market_conditions.get("regime", "normal")
        volatility_level = market_conditions.get("volatility", "moderate")

        session = SimulationSession(
            user_id=user_id,
            name=name,
            description=description,
            status="pending",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),  # Default 30 days
            initial_capital=initial_balance,
            current_balance=initial_balance,
            market_regime=market_regime,
            volatility_level=volatility_level,
            commission_per_trade=Decimal("0.001"),  # 0.1%
            slippage_model="fixed",
            slippage_amount=Decimal("0.0005"),  # 0.05%
            strategy_config=strategy_config,
            random_seed=self.random_seed,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session.id

    async def list_sessions(self, user_id: UUID) -> List[SimulationSession]:
        """List all simulation sessions for a user."""
        result = await self.db.execute(
            select(SimulationSession)
            .where(SimulationSession.user_id == user_id)
            .order_by(SimulationSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_session(self, session_id: UUID, user_id: UUID) -> Optional[SimulationSession]:
        """Get a simulation session by ID."""
        result = await self.db.execute(
            select(SimulationSession)
            .where(
                and_(
                    SimulationSession.id == session_id,
                    SimulationSession.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def start_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Start a simulation session."""
        result = await self.db.execute(
            update(SimulationSession)
            .where(
                and_(
                    SimulationSession.id == session_id,
                    SimulationSession.user_id == user_id,
                    SimulationSession.status == "pending"
                )
            )
            .values(status="running")
        )
        await self.db.commit()
        return result.rowcount > 0

    async def stop_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Stop a running simulation session."""
        result = await self.db.execute(
            update(SimulationSession)
            .where(
                and_(
                    SimulationSession.id == session_id,
                    SimulationSession.user_id == user_id,
                    SimulationSession.status == "running"
                )
            )
            .values(status="completed")
        )
        await self.db.commit()
        return result.rowcount > 0

    async def place_order(
        self,
        session_id: UUID,
        user_id: UUID,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: Optional[Decimal] = None
    ) -> Optional[UUID]:
        """Place an order in a simulation session."""
        # Get session
        session = await self.get_session(session_id, user_id)
        if not session or session.status != "running":
            return None

        # Get current market price
        try:
            market_price = await self._get_market_price(symbol)
        except Exception:
            return None

        # Apply slippage and commission
        slippage = self._calculate_slippage(session, market_price, quantity, order_type)
        commission = market_price * Decimal(str(quantity)) * session.commission_per_trade

        if side == "buy":
            executed_price = market_price + slippage
            total_cost = (executed_price * Decimal(str(quantity))) + commission

            # Check if sufficient balance
            if session.current_balance < total_cost:
                return None

            session.current_balance -= total_cost
        else:  # sell
            executed_price = market_price - slippage
            total_value = (executed_price * Decimal(str(quantity))) - commission
            session.current_balance += total_value

        # Create order record
        order = SimulationOrder(
            session_id=session_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=Decimal(str(quantity)),
            requested_price=price,
            executed_price=executed_price,
            slippage_amount=slippage,
            commission=commission,
            status="filled",
            order_timestamp=datetime.now(timezone.utc),
            execution_timestamp=datetime.now(timezone.utc),
            market_price_at_order=market_price,
            market_volatility=self._calculate_volatility(session.volatility_level),
        )

        # Update or create position
        await self._update_position(session, order)

        # Update session metrics
        session.total_trades += 1

        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)

        return order.id

    async def get_session_orders(self, session_id: UUID, user_id: UUID) -> List[SimulationOrder]:
        """Get all orders for a simulation session."""
        result = await self.db.execute(
            select(SimulationOrder)
            .where(SimulationOrder.session_id == session_id)
            .order_by(SimulationOrder.order_timestamp.desc())
        )
        return list(result.scalars().all())

    async def get_session_positions(self, session_id: UUID, user_id: UUID) -> List[SimulationPosition]:
        """Get current positions for a simulation session."""
        result = await self.db.execute(
            select(SimulationPosition)
            .where(SimulationPosition.session_id == session_id)
        )
        return list(result.scalars().all())

    async def get_session_metrics(self, session_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a simulation session."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None

        # Get all results
        result = await self.db.execute(
            select(SimulationResult)
            .where(SimulationResult.session_id == session_id)
            .order_by(SimulationResult.timestamp)
        )
        results = list(result.scalars().all())

        if not results:
            return {
                "total_return": 0.0,
                "total_return_percent": 0.0,
                "sharpe_ratio": None,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "total_trades": session.total_trades,
                "avg_trade_return": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
            }

        # Calculate metrics
        portfolio_values = [float(r.portfolio_value) for r in results]
        returns = []

        for i in range(1, len(portfolio_values)):
            ret = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            returns.append(ret)

        total_return = ((portfolio_values[-1] - float(session.initial_capital)) / float(session.initial_capital)) * 100
        max_drawdown = max(r.max_drawdown for r in results)

        # Calculate Sharpe ratio
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else None
        else:
            sharpe_ratio = None

        # Get trade returns
        orders_result = await self.db.execute(
            select(SimulationOrder)
            .where(
                and_(
                    SimulationOrder.session_id == session_id,
                    SimulationOrder.status == "filled"
                )
            )
        )
        orders = list(orders_result.scalars().all())

        trade_returns = []
        for order in orders:
            if order.side == "sell":
                # Calculate return for sell orders (assuming we have position data)
                # This is simplified - in reality we'd track entry/exit pairs
                pass

        return {
            "total_return": total_return,
            "total_return_percent": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": results[-1].win_rate if results else 0.0,
            "total_trades": session.total_trades,
            "avg_trade_return": np.mean(trade_returns) if trade_returns else 0.0,
            "largest_win": max(trade_returns) if trade_returns else 0.0,
            "largest_loss": min(trade_returns) if trade_returns else 0.0,
        }

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Delete a simulation session."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        await self.db.delete(session)
        await self.db.commit()
        return True

    async def _get_market_price(self, symbol: str) -> Decimal:
        """Get current market price for a symbol."""
        # In a real implementation, this would call the market data service
        # For now, return a mock price
        base_prices = {
            "AAPL": Decimal("150.00"),
            "GOOGL": Decimal("2800.00"),
            "MSFT": Decimal("300.00"),
            "TSLA": Decimal("200.00"),
            "NVDA": Decimal("400.00"),
            "AMZN": Decimal("3000.00"),
            "META": Decimal("300.00"),
            "NFLX": Decimal("400.00"),
        }

        if symbol in base_prices:
            # Add some random variation
            variation = Decimal(str(random.uniform(-0.02, 0.02)))
            return base_prices[symbol] * (Decimal("1") + variation)

        # Default price for unknown symbols
        return Decimal("100.00")

    def _calculate_slippage(
        self,
        session: SimulationSession,
        market_price: Decimal,
        quantity: int,
        order_type: str,
    ) -> Decimal:
        """Calculate realistic slippage."""
        if session.slippage_model == "none":
            return Decimal("0")
        elif session.slippage_model == "fixed":
            return session.slippage_amount
        elif session.slippage_model == "percentage":
            return market_price * session.slippage_amount
        else:  # volume_based or default
            volume_factor = min(quantity / 1000, 1.0)
            return market_price * session.slippage_amount * Decimal(str(volume_factor))

    def _calculate_volatility(self, volatility_level: str) -> float:
        """Convert volatility level to numerical value."""
        vol_map = {
            "low": 0.05,
            "moderate": 0.15,
            "high": 0.30,
            "extreme": 0.60,
        }
        return vol_map.get(volatility_level, 0.15)

    async def _update_position(self, session: SimulationSession, order: SimulationOrder) -> None:
        """Update or create position based on order execution."""
        # Get existing position
        result = await self.db.execute(
            select(SimulationPosition)
            .where(
                and_(
                    SimulationPosition.session_id == session.id,
                    SimulationPosition.symbol == order.symbol
                )
            )
        )
        position = result.scalar_one_or_none()

        if position is None:
            # Create new position
            position = SimulationPosition(
                session_id=session.id,
                symbol=order.symbol,
                quantity=order.quantity if order.side == "buy" else -order.quantity,
                average_cost=order.executed_price,
                current_price=order.executed_price,
                market_value=order.executed_price * order.quantity,
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                opened_at=order.execution_timestamp,
                peak_value=order.executed_price * order.quantity,
            )
            self.db.add(position)
        else:
            # Update existing position
            if order.side == "buy":
                # Calculate new average cost
                total_quantity = position.quantity + order.quantity
                total_cost = (position.quantity * position.average_cost) + (order.quantity * order.executed_price)
                position.average_cost = total_cost / total_quantity
                position.quantity = total_quantity
            else:  # sell
                # Reduce position
                position.quantity -= order.quantity
                # Calculate realized P&L
                realized_pnl = (order.executed_price - position.average_cost) * order.quantity
                position.realized_pnl += realized_pnl

            position.current_price = order.executed_price
            position.market_value = position.quantity * order.executed_price
            position.unrealized_pnl = (position.current_price - position.average_cost) * position.quantity
            position.last_updated = datetime.now(timezone.utc)

            # Update drawdown
            if position.market_value > position.peak_value:
                position.peak_value = position.market_value

            if position.peak_value > 0:
                current_drawdown = ((position.peak_value - position.market_value) / position.peak_value) * 100
                position.max_drawdown = max(position.max_drawdown, current_drawdown)
        """Create a new simulation session."""

        session = SimulationSession(
            user_id=user_id,
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            market_regime=market_condition,
            volatility_level=volatility_level,
            commission_per_trade=commission_per_trade,
            slippage_model=slippage_model,
            slippage_amount=slippage_amount,
            max_position_size=max_position_size,
            max_daily_loss=max_daily_loss,
            strategy_config=strategy_config or {},
            random_seed=self.random_seed,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def run_simulation(self, session_id: UUID) -> Dict[str, Any]:
        """Execute a complete simulation run."""
        try:
            # Get simulation session
            session = await self.db.get(SimulationSession, session_id)
            if not session:
                return {"error": "Simulation session not found"}

            if session.status != "pending":
                return {"error": f"Simulation already {session.status}"}

            # Update status to running
            session.status = "running"
            await self.db.commit()

            start_time = datetime.now(timezone.utc)

            # Set random seed if specified
            if session.random_seed:
                self.set_random_seed(session.random_seed)

            # Initialize portfolio
            portfolio_value = session.initial_capital
            cash_balance = session.initial_capital

            # Generate trading dates (business days)
            trading_dates = self._generate_trading_dates(session.start_date, session.end_date)

            # Initialize results tracking
            results = []
            positions: Dict[str, SimulationPosition] = {}
            daily_pnl = Decimal("0")

            # Main simulation loop
            for i, current_date in enumerate(trading_dates):
                try:
                    # Generate market prices for this day
                    market_prices = await self._generate_market_prices(current_date, session.market_regime, session.volatility_level)

                    # Execute strategy (placeholder - would be replaced with actual strategy)
                    orders = await self._execute_strategy(session, current_date, market_prices, positions, cash_balance)

                    # Process orders with realistic execution
                    for order in orders:
                        execution_result = await self._execute_order_simulation(
                            session, order, market_prices, current_date
                        )

                        if execution_result["success"]:
                            # Update positions and cash
                            cash_balance = execution_result["new_cash_balance"]
                            positions = execution_result["updated_positions"]

                            # Create simulation order record
                            sim_order = SimulationOrder(
                                session_id=session_id,
                                symbol=order["symbol"],
                                side=order["side"],
                                order_type=order["order_type"],
                                quantity=order["quantity"],
                                requested_price=order.get("price"),
                                executed_price=execution_result["executed_price"],
                                slippage_amount=execution_result["slippage"],
                                commission=execution_result["commission"],
                                status="filled",
                                order_timestamp=current_date,
                                execution_timestamp=current_date,
                                market_price_at_order=market_prices.get(order["symbol"]),
                                market_volatility=self._calculate_volatility(session.volatility_level),
                            )
                            self.db.add(sim_order)

                    # Update position P&L
                    for symbol, position in positions.items():
                        current_price = market_prices.get(symbol, position.current_price or Decimal("100"))
                        position.update_pnl(current_price)

                    # Calculate daily portfolio value
                    total_position_value = sum(
                        (pos.market_value or Decimal("0")) for pos in positions.values()
                    )
                    portfolio_value = cash_balance + total_position_value

                    # Calculate daily return
                    daily_return = 0.0
                    if i > 0 and results:
                        prev_value = results[-1].portfolio_value
                        if prev_value > 0:
                            daily_return = float((portfolio_value - prev_value) / prev_value) * 100

                    # Calculate cumulative return
                    cumulative_return = float((portfolio_value - session.initial_capital) / session.initial_capital) * 100

                    # Calculate drawdown
                    max_drawdown = 0.0
                    if results:
                        peak_value = max(r.portfolio_value for r in results + [type('obj', (object,), {'portfolio_value': portfolio_value})()])
                        if peak_value > 0:
                            max_drawdown = float((peak_value - portfolio_value) / peak_value) * 100

                    # Count trades
                    total_trades = len([o for o in orders if o.get("executed", False)])
                    winning_trades = len([p for p in positions.values() if p.total_pnl > 0])
                    losing_trades = len([p for p in positions.values() if p.total_pnl < 0])

                    # Create result snapshot
                    result = SimulationResult(
                        session_id=session_id,
                        timestamp=current_date,
                        portfolio_value=portfolio_value,
                        cash_balance=cash_balance,
                        cumulative_return=cumulative_return,
                        daily_return=daily_return,
                        volatility=self._calculate_volatility(session.volatility_level),
                        sharpe_ratio=self._calculate_sharpe_ratio(results + [type('obj', (object,), {'daily_return': daily_return})()]),
                        max_drawdown=max_drawdown,
                        total_trades=sum(len(results) + 1 for r in results) if results else total_trades,
                        winning_trades=winning_trades,
                        losing_trades=losing_trades,
                        vix_level=self._calculate_vix_level(session.volatility_level),
                        market_regime=session.market_regime,
                    )
                    self.db.add(result)
                    results.append(result)

                    # Commit daily results
                    await self.db.commit()

                except Exception as e:
                    logger.error(f"Error processing day {current_date}: {e}")
                    continue

            # Update session with final results
            session.status = "completed"
            session.final_value = portfolio_value
            session.total_return = (float(portfolio_value) - float(session.initial_capital)) / float(session.initial_capital) * 100
            session.sharpe_ratio = self._calculate_sharpe_ratio(results)
            session.max_drawdown = max((r.max_drawdown for r in results), default=0.0)
            session.win_rate = sum(r.winning_trades for r in results) / sum(r.total_trades for r in results) * 100 if results else 0
            session.total_trades = sum(r.total_trades for r in results)
            session.execution_time_seconds = int((datetime.now(timezone.utc) - start_time).total_seconds())

            await self.db.commit()

            return {
                "success": True,
                "session_id": session_id,
                "final_value": float(portfolio_value),
                "total_return": session.total_return,
                "sharpe_ratio": session.sharpe_ratio,
                "max_drawdown": session.max_drawdown,
                "win_rate": session.win_rate,
                "total_trades": session.total_trades,
                "execution_time_seconds": session.execution_time_seconds,
            }

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            # Update session status to failed
            if 'session' in locals():
                session.status = "failed"
                await self.db.commit()
            return {"error": str(e)}

    async def _generate_market_prices(
        self,
        date: datetime,
        market_regime: str,
        volatility_level: str
    ) -> Dict[str, Decimal]:
        """Generate realistic market prices for simulation."""
        # For now, use a simple random walk model
        # In production, this would use historical data or more sophisticated models

        base_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "NFLX"]
        prices = {}

        # Base prices (would come from historical data)
        base_prices = {
            "AAPL": Decimal("150.00"),
            "GOOGL": Decimal("2800.00"),
            "MSFT": Decimal("300.00"),
            "TSLA": Decimal("200.00"),
            "NVDA": Decimal("400.00"),
            "AMZN": Decimal("3000.00"),
            "META": Decimal("300.00"),
            "NFLX": Decimal("400.00"),
        }

        # Volatility multipliers
        vol_multipliers = {
            "low": 0.005,
            "moderate": 0.015,
            "high": 0.035,
            "extreme": 0.08,
        }

        # Market regime adjustments
        regime_multipliers = {
            "bull": 1.02,
            "bear": 0.98,
            "sideways": 1.0,
            "volatile": 1.0,
            "normal": 1.0,
        }

        vol_multiplier = vol_multipliers.get(volatility_level, 0.015)
        regime_multiplier = regime_multipliers.get(market_regime, 1.0)

        for symbol in base_symbols:
            base_price = base_prices[symbol]

            # Generate random return
            daily_return = np.random.normal(0, vol_multiplier)

            # Apply regime adjustment
            daily_return *= regime_multiplier

            # Calculate new price
            price_change = base_price * Decimal(str(daily_return))
            new_price = base_price + price_change

            # Ensure positive price
            new_price = max(new_price, base_price * Decimal("0.1"))

            prices[symbol] = new_price.quantize(Decimal("0.01"))

        return prices

    async def _execute_strategy(
        self,
        session: SimulationSession,
        current_date: datetime,
        market_prices: Dict[str, Decimal],
        positions: Dict[str, SimulationPosition],
        cash_balance: Decimal,
    ) -> List[Dict[str, Any]]:
        """Execute trading strategy (placeholder for actual strategy logic)."""
        # This is a placeholder - in production, this would implement actual trading strategies
        # For now, implement a simple momentum strategy as an example

        orders = []

        # Simple strategy: buy if price > moving average (simplified)
        for symbol, price in market_prices.items():
            # Random decision for demo purposes
            if random.random() < 0.1:  # 10% chance to trade each day
                if random.random() < 0.6:  # 60% buy, 40% sell
                    # Buy order
                    max_quantity = int(cash_balance / price * Decimal("0.1"))  # Max 10% of cash
                    if max_quantity > 0:
                        quantity = random.randint(1, max(1, min(max_quantity, 100)))
                        orders.append({
                            "symbol": symbol,
                            "side": "buy",
                            "order_type": "market",
                            "quantity": Decimal(str(quantity)),
                        })
                else:
                    # Sell order (if we have position)
                    if symbol in positions and positions[symbol].quantity > 0:
                        quantity = min(positions[symbol].quantity, Decimal(str(random.randint(1, 10))))
                        orders.append({
                            "symbol": symbol,
                            "side": "sell",
                            "order_type": "market",
                            "quantity": quantity,
                        })

        return orders

    async def _execute_order_simulation(
        self,
        session: SimulationSession,
        order: Dict[str, Any],
        market_prices: Dict[str, Decimal],
        execution_time: datetime,
    ) -> Dict[str, Any]:
        """Execute order with realistic slippage and commissions."""
        try:
            symbol = order["symbol"]
            side = order["side"]
            quantity = order["quantity"]
            order_type = order["order_type"]

            # Get market price
            market_price = market_prices.get(symbol)
            if not market_price:
                return {"success": False, "error": f"No market price for {symbol}"}

            # Apply slippage
            slippage = self._calculate_slippage(session, market_price, quantity, order_type)
            if side == "buy":
                executed_price = market_price + slippage
            else:
                executed_price = market_price - slippage

            # Ensure positive price
            executed_price = max(executed_price, Decimal("0.01"))

            # Calculate commission
            commission = (executed_price * quantity * session.commission_per_trade).quantize(Decimal("0.01"))

            # Calculate total cost
            total_cost = (executed_price * quantity) + commission

            # Check if we have enough cash for buy orders
            if side == "buy":
                required_cash = total_cost
                # Note: In real implementation, check against cash_balance passed in

            return {
                "success": True,
                "executed_price": executed_price,
                "slippage": slippage,
                "commission": commission,
                "total_cost": total_cost,
                "new_cash_balance": Decimal("0"),  # Would be calculated properly
                "updated_positions": {},  # Would be updated properly
            }

        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_slippage(
        self,
        session: SimulationSession,
        market_price: Decimal,
        quantity: Decimal,
        order_type: str,
    ) -> Decimal:
        """Calculate realistic slippage based on session parameters."""
        if session.slippage_model == "none":
            return Decimal("0")
        elif session.slippage_model == "fixed":
            return session.slippage_amount
        elif session.slippage_model == "percentage":
            return market_price * session.slippage_amount
        elif session.slippage_model == "volume_based":
            # Larger orders have more slippage
            volume_factor = min(float(quantity) / 1000, 1.0)  # Cap at 1000 shares
            return market_price * session.slippage_amount * Decimal(str(volume_factor))
        else:
            return session.slippage_amount

    def _calculate_volatility(self, volatility_level: str) -> float:
        """Convert volatility level to numerical value."""
        vol_map = {
            "low": 0.05,
            "moderate": 0.15,
            "high": 0.30,
            "extreme": 0.60,
        }
        return vol_map.get(volatility_level, 0.15)

    def _calculate_vix_level(self, volatility_level: str) -> float:
        """Convert volatility level to VIX equivalent."""
        vix_map = {
            "low": 12.0,
            "moderate": 18.0,
            "high": 25.0,
            "extreme": 35.0,
        }
        return vix_map.get(volatility_level, 18.0)

    def _calculate_sharpe_ratio(self, results: List) -> float | None:
        """Calculate Sharpe ratio from results."""
        if len(results) < 2:
            return None

        returns = [r.daily_return for r in results if r.daily_return is not None]
        if not returns:
            return None

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return None

        # Assuming risk-free rate of 2%
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        return (avg_return - risk_free_rate) / std_return * np.sqrt(252)  # Annualized

    def _generate_trading_dates(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Generate list of business days between start and end dates."""
        dates = []
        current = start_date

        while current <= end_date:
            # Skip weekends (Saturday = 5, Sunday = 6)
            if current.weekday() < 5:
                dates.append(current)
            current += timedelta(days=1)

        return dates

    async def get_simulation_results(self, session_id: UUID) -> Dict[str, Any]:
        """Get comprehensive simulation results and analytics."""
        try:
            # Get session
            session = await self.db.get(SimulationSession, session_id)
            if not session:
                return {"error": "Simulation session not found"}

            # Get results
            results_result = await self.db.execute(
                select(SimulationResult)
                .where(SimulationResult.session_id == session_id)
                .order_by(SimulationResult.timestamp)
            )
            results = results_result.scalars().all()

            # Get orders
            orders_result = await self.db.execute(
                select(SimulationOrder)
                .where(SimulationOrder.session_id == session_id)
                .order_by(SimulationOrder.execution_timestamp)
            )
            orders = orders_result.scalars().all()

            # Get final positions
            positions_result = await self.db.execute(
                select(SimulationPosition)
                .where(SimulationPosition.session_id == session_id)
            )
            positions = positions_result.scalars().all()

            # Calculate performance metrics
            if results:
                portfolio_values = [float(r.portfolio_value) for r in results]
                returns = []

                for i in range(1, len(portfolio_values)):
                    ret = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
                    returns.append(ret)

                metrics = {
                    "total_return": session.total_return,
                    "sharpe_ratio": session.sharpe_ratio,
                    "max_drawdown": session.max_drawdown,
                    "win_rate": session.win_rate,
                    "total_trades": session.total_trades,
                    "avg_daily_return": np.mean(returns) * 100 if returns else 0,
                    "volatility": np.std(returns) * 100 if returns else 0,
                    "best_day": max(returns) * 100 if returns else 0,
                    "worst_day": min(returns) * 100 if returns else 0,
                }
            else:
                metrics = {}

            return {
                "session": {
                    "id": session.id,
                    "name": session.name,
                    "status": session.status,
                    "start_date": session.start_date.isoformat(),
                    "end_date": session.end_date.isoformat(),
                    "initial_capital": float(session.initial_capital),
                    "final_value": float(session.final_value) if session.final_value else None,
                    "market_regime": session.market_regime,
                    "volatility_level": session.volatility_level,
                },
                "performance": metrics,
                "results": [
                    {
                        "timestamp": r.timestamp.isoformat(),
                        "portfolio_value": float(r.portfolio_value),
                        "cumulative_return": r.cumulative_return,
                        "daily_return": r.daily_return,
                        "max_drawdown": r.max_drawdown,
                        "total_trades": r.total_trades,
                        "win_rate": r.win_rate,
                    }
                    for r in results
                ],
                "orders": [
                    {
                        "symbol": o.symbol,
                        "side": o.side,
                        "quantity": float(o.quantity),
                        "executed_price": float(o.executed_price) if o.executed_price else None,
                        "commission": float(o.commission),
                        "timestamp": o.execution_timestamp.isoformat() if o.execution_timestamp else None,
                    }
                    for o in orders
                ],
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": float(p.quantity),
                        "average_cost": float(p.average_cost),
                        "current_price": float(p.current_price) if p.current_price else None,
                        "unrealized_pnl": float(p.unrealized_pnl),
                        "realized_pnl": float(p.realized_pnl),
                        "max_drawdown": p.max_drawdown,
                    }
                    for p in positions
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get simulation results: {e}")
            return {"error": str(e)}