"""
trading_service.py — Core trading execution engine and position management.

Handles order lifecycle, position tracking, P&L calculations, and risk management.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vanguard_signal.schema.models.trading import Portfolio, Order, Position, RiskMetrics
from vanguard_signal.schema.models import User
from vanguard_signal.market_data import MarketDataService

logger = logging.getLogger(__name__)


class TradingService:
    """Core trading execution engine for order processing and position management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data = MarketDataService(db)

    async def validate_order(
        self,
        portfolio_id: UUID,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "market"
    ) -> dict[str, str]:
        """
        Validate an order before execution.

        Returns empty dict if valid, or dict with error messages.
        """
        errors = {}

        # Get portfolio
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            errors["portfolio"] = "Portfolio not found"
            return errors

        if not portfolio.is_active:
            errors["portfolio"] = "Portfolio is not active"

        # Check portfolio risk limits
        if portfolio.max_position_size:
            # Use cash balance as denominator for new portfolios with zero total value
            denominator = portfolio.total_value if portfolio.total_value > 0 else portfolio.cash_balance
            if denominator <= 0:
                errors["portfolio"] = "Portfolio has no available funds"
            else:
                position_size_pct = (quantity * (price or Decimal("100.00"))) / denominator
                if position_size_pct > portfolio.max_position_size:
                    errors["position_size"] = f"Order exceeds maximum position size limit of {portfolio.max_position_size:.2%}"

        # Check short selling restrictions
        if side.lower() == "sell" and not portfolio.allow_short_selling:
            # Check if we have enough position to sell
            position = await self._get_position(portfolio_id, symbol)
            if not position or position.quantity < quantity:
                errors["short_selling"] = "Short selling not allowed and insufficient position"

        # Check margin trading restrictions
        if side.lower() == "sell" and not portfolio.allow_margin:
            # For margin trading validation, we'd need more complex logic
            # For now, just check basic constraints
            pass

        return errors

    async def execute_order(
        self,
        order: Order,
        execution_price: Optional[Decimal] = None
    ) -> dict[str, any]:
        """
        Execute an order and update positions.

        Returns execution result with status and details.
        Note: Transaction management should be handled by the caller.
        """
        try:
            # Validate order
            validation_errors = await self.validate_order(
                order.portfolio_id,
                order.symbol,
                order.side,
                order.quantity,
                order.price,
                order.order_type
            )

            if validation_errors:
                order.status = "rejected"
                return {
                    "success": False,
                    "status": "rejected",
                    "errors": validation_errors
                }

            # Determine execution price
            if execution_price:
                fill_price = execution_price
            elif order.order_type == "market":
                # For paper trading, use market price
                fill_price = await self._get_market_price(order.symbol)
            elif order.price:
                fill_price = order.price
            else:
                fill_price = await self._get_market_price(order.symbol)

            # Update order status
            order.status = "filled"
            order.filled_quantity = order.quantity
            order.average_fill_price = fill_price

            # Update position
            await self._update_position(order, fill_price)

            # Update portfolio P&L
            await self._update_portfolio_pnl(order.portfolio_id)

            return {
                "success": True,
                "status": "filled",
                "fill_price": fill_price,
                "filled_quantity": order.quantity
            }

        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            order.status = "failed"
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }

    async def cancel_order(self, order_id: UUID, user_id: UUID) -> dict[str, any]:
        """Cancel a pending order."""
        try:
            # Get order with portfolio check
            order = await self.db.execute(
                select(Order)
                .join(Portfolio)
                .where(
                    and_(
                        Order.id == order_id,
                        Portfolio.user_id == user_id,
                        Order.status == "pending"
                    )
                )
            )
            order = order.scalar_one_or_none()

            if not order:
                return {
                    "success": False,
                    "error": "Order not found or not cancellable"
                }

            order.status = "cancelled"
            await self.db.commit()

            return {"success": True, "status": "cancelled"}

        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_portfolio_summary(self, portfolio_id: UUID) -> dict[str, any]:
        """Get comprehensive portfolio summary with positions and P&L."""
        try:
            # Get portfolio
            portfolio = await self.db.get(Portfolio, portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}

            # Get all positions
            positions_result = await self.db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            )
            positions = positions_result.scalars().all()

            # Calculate totals
            total_market_value = sum(
                (pos.market_value or Decimal("0")) for pos in positions
            )
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
            total_realized_pnl = sum(pos.realized_pnl for pos in positions)

            # Update portfolio totals
            portfolio.total_value = portfolio.cash_balance + total_market_value

            return {
                "portfolio": {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "cash_balance": portfolio.cash_balance,
                    "total_value": portfolio.total_value,
                    "unrealized_pnl": total_unrealized_pnl,
                    "realized_pnl": total_realized_pnl,
                    "currency": portfolio.currency,
                    "is_paper_trading": portfolio.is_paper_trading
                },
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "quantity": pos.quantity,
                        "average_cost": pos.average_cost,
                        "current_price": pos.current_price,
                        "market_value": pos.market_value,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "realized_pnl": pos.realized_pnl
                    }
                    for pos in positions
                ],
                "summary": {
                    "total_positions": len(positions),
                    "total_market_value": total_market_value,
                    "total_pnl": total_unrealized_pnl + total_realized_pnl
                }
            }

        except Exception as e:
            logger.error(f"Portfolio summary failed: {e}")
            return {"error": str(e)}

    async def _get_position(self, portfolio_id: UUID, symbol: str) -> Optional[Position]:
        """Get or create position for a symbol."""
        result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.symbol == symbol
                )
            )
        )
        return result.scalar_one_or_none()

    async def _update_position(self, order: Order, fill_price: Decimal) -> None:
        """Update position based on filled order."""
        position = await self._get_position(order.portfolio_id, order.symbol)

        if not position:
            # Create new position
            from datetime import datetime, timezone
            position = Position(
                portfolio_id=order.portfolio_id,
                symbol=order.symbol,
                quantity=Decimal("0"),
                average_cost=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                opened_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            self.db.add(position)

        # Calculate order value
        order_value = order.quantity * fill_price

        if order.side.lower() == "buy":
            # Update average cost and quantity
            total_cost = (position.quantity * position.average_cost) + order_value
            position.quantity += order.quantity
            if position.quantity > 0:
                position.average_cost = total_cost / position.quantity

        elif order.side.lower() == "sell":
            if position.quantity >= order.quantity:
                # Calculate realized P&L
                realized_pnl = (fill_price - position.average_cost) * order.quantity
                position.realized_pnl += realized_pnl
                position.quantity -= order.quantity

                # If position closed, reset average cost
                if position.quantity == 0:
                    position.average_cost = Decimal("0")
            else:
                # Short selling scenario (if allowed)
                position.quantity -= order.quantity
                # For short positions, average cost represents the short price
                position.average_cost = fill_price

        # Update market value and unrealized P&L
        if position.quantity != 0:
            # Mock current price for paper trading
            current_price = await self._get_market_price(order.symbol)
            position.current_price = current_price
            position.market_value = position.quantity * current_price
            position.unrealized_pnl = (current_price - position.average_cost) * position.quantity
        else:
            position.current_price = None
            position.market_value = None
            position.unrealized_pnl = Decimal("0")

        position.last_updated = datetime.now(timezone.utc)

    async def _update_portfolio_pnl(self, portfolio_id: UUID) -> None:
        """Update portfolio total value and P&L."""
        # Get all positions
        positions_result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions = positions_result.scalars().all()

        total_market_value = sum(
            (pos.market_value or Decimal("0")) for pos in positions
        )

        # Update portfolio
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio:
            portfolio.total_value = portfolio.cash_balance + total_market_value

    async def _get_market_price(self, symbol: str) -> Decimal:
        """Get current market price for a symbol."""
        price = await self.market_data.get_current_price(symbol)
        return Decimal(str(price)).quantize(Decimal("0.01")) if price else Decimal("100.00")

    async def calculate_portfolio_performance(self, portfolio_id: UUID, period_days: int = 30) -> dict[str, any]:
        """Calculate portfolio performance metrics over a time period."""
        try:
            from datetime import datetime, timezone, timedelta

            # Get portfolio
            portfolio = await self.db.get(Portfolio, portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}

            # Get historical orders for performance calculation
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
            orders_result = await self.db.execute(
                select(Order).where(
                    and_(
                        Order.portfolio_id == portfolio_id,
                        Order.status == "filled",
                        Order.filled_at >= cutoff_date
                    )
                ).order_by(Order.filled_at)
            )
            orders = orders_result.scalars().all()

            if not orders:
                return {
                    "total_return": 0.0,
                    "sharpe_ratio": None,
                    "volatility": None,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                    "total_trades": 0
                }

            # Calculate returns from trades
            returns = []
            cumulative_return = 0.0
            peak_value = portfolio.cash_balance
            max_drawdown = 0.0
            winning_trades = 0

            for order in orders:
                if order.side.lower() == "buy":
                    # Investment
                    trade_value = float(order.quantity * order.average_fill_price)
                    cumulative_return -= trade_value
                else:
                    # Sale - calculate P&L
                    entry_orders = [o for o in orders if o.symbol == order.symbol and o.side.lower() == "buy" and o.filled_at < order.filled_at]
                    if entry_orders:
                        avg_entry_price = sum(float(o.average_fill_price) for o in entry_orders) / len(entry_orders)
                        pnl = float(order.quantity) * (float(order.average_fill_price) - avg_entry_price)
                        cumulative_return += pnl
                        if pnl > 0:
                            winning_trades += 1

                        # Track drawdown
                        current_value = portfolio.cash_balance + cumulative_return
                        if current_value > peak_value:
                            peak_value = current_value
                        drawdown = (peak_value - current_value) / peak_value
                        max_drawdown = max(max_drawdown, drawdown)

            total_return_pct = (cumulative_return / portfolio.cash_balance) * 100 if portfolio.cash_balance > 0 else 0
            win_rate = (winning_trades / len([o for o in orders if o.side.lower() == "sell"])) * 100 if orders else 0

            # Calculate Sharpe ratio (simplified - daily returns)
            sharpe_ratio = total_return_pct / 10.0 if period_days > 0 else None  # Rough approximation

            return {
                "total_return": total_return_pct,
                "sharpe_ratio": sharpe_ratio,
                "volatility": None,  # Would need daily returns series
                "max_drawdown": max_drawdown * 100,
                "win_rate": win_rate,
                "total_trades": len(orders),
                "period_days": period_days
            }

        except Exception as e:
            logger.error(f"Portfolio performance calculation failed: {e}")
            return {"error": str(e)}

    async def rebalance_portfolio(self, portfolio_id: UUID, target_allocations: dict[str, float]) -> dict[str, any]:
        """Rebalance portfolio to target allocations."""
        try:
            # Get portfolio and positions
            portfolio = await self.db.get(Portfolio, portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}

            positions_result = await self.db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            )
            positions = positions_result.scalars().all()

            total_value = portfolio.total_value
            if total_value <= 0:
                return {"error": "Portfolio has no value to rebalance"}

            # Calculate current allocations
            current_allocations = {}
            for pos in positions:
                if pos.market_value and pos.market_value > 0:
                    current_allocations[pos.symbol] = float(pos.market_value / total_value)

            # Calculate required trades
            trades = []
            for symbol, target_pct in target_allocations.items():
                current_pct = current_allocations.get(symbol, 0.0)
                target_value = total_value * target_pct
                current_value = total_value * current_pct

                if target_value > current_value:
                    # Need to buy
                    buy_amount = target_value - current_value
                    if buy_amount > 0:
                        trades.append({
                            "symbol": symbol,
                            "side": "buy",
                            "amount": buy_amount
                        })
                elif current_value > target_value:
                    # Need to sell
                    sell_amount = current_value - target_value
                    if sell_amount > 0:
                        trades.append({
                            "symbol": symbol,
                            "side": "sell",
                            "amount": sell_amount
                        })

            return {
                "current_allocations": current_allocations,
                "target_allocations": target_allocations,
                "required_trades": trades,
                "total_value": float(total_value)
            }

        except Exception as e:
            logger.error(f"Portfolio rebalancing failed: {e}")
            return {"error": str(e)}

    async def get_portfolio_composition(self, portfolio_id: UUID) -> dict[str, any]:
        """Get detailed portfolio composition analysis."""
        try:
            # Get portfolio and positions
            portfolio = await self.db.get(Portfolio, portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}

            positions_result = await self.db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            )
            positions = positions_result.scalars().all()

            total_value = portfolio.total_value
            if total_value <= 0:
                return {
                    "cash_balance": float(portfolio.cash_balance),
                    "total_value": 0.0,
                    "positions": [],
                    "sector_breakdown": {},
                    "risk_breakdown": {}
                }

            # Analyze positions
            position_data = []
            sector_breakdown = {}
            risk_breakdown = {"low": 0, "medium": 0, "high": 0}

            for pos in positions:
                if pos.market_value and pos.market_value > 0:
                    weight = float(pos.market_value / total_value)
                    pnl_pct = float(pos.unrealized_pnl / pos.market_value) if pos.market_value > 0 else 0

                    position_data.append({
                        "symbol": pos.symbol,
                        "quantity": float(pos.quantity),
                        "average_cost": float(pos.average_cost),
                        "current_price": float(pos.current_price) if pos.current_price else None,
                        "market_value": float(pos.market_value),
                        "unrealized_pnl": float(pos.unrealized_pnl),
                        "weight": weight * 100,
                        "pnl_percentage": pnl_pct * 100
                    })

                    # Simple sector classification (would need proper sector data)
                    sector = "Technology" if pos.symbol in ["AAPL", "GOOGL", "MSFT"] else "Other"
                    sector_breakdown[sector] = sector_breakdown.get(sector, 0) + weight

                    # Risk classification based on volatility (simplified)
                    if pnl_pct > 0.05:
                        risk_breakdown["high"] += weight
                    elif pnl_pct > 0.02:
                        risk_breakdown["medium"] += weight
                    else:
                        risk_breakdown["low"] += weight

            return {
                "cash_balance": float(portfolio.cash_balance),
                "total_value": float(total_value),
                "positions": sorted(position_data, key=lambda x: x["market_value"], reverse=True),
                "sector_breakdown": sector_breakdown,
                "risk_breakdown": risk_breakdown,
                "total_positions": len(position_data)
            }

        except Exception as e:
            logger.error(f"Portfolio composition analysis failed: {e}")
            return {"error": str(e)}

    async def check_portfolio_alerts(self, portfolio_id: UUID) -> dict[str, any]:
        """Check portfolio for alert conditions and return any triggered alerts."""
        try:
            # Get portfolio and positions
            portfolio = await self.db.get(Portfolio, portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}

            positions_result = await self.db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            )
            positions = positions_result.scalars().all()

            alerts = []

            # Check portfolio-level alerts
            total_pnl = sum(pos.unrealized_pnl + pos.realized_pnl for pos in positions)
            pnl_percentage = (total_pnl / portfolio.total_value) * 100 if portfolio.total_value > 0 else 0

            if portfolio.max_daily_loss and pnl_percentage <= -portfolio.max_daily_loss:
                alerts.append({
                    "type": "portfolio_loss",
                    "severity": "high",
                    "message": f"Portfolio loss of {pnl_percentage:.1f}% exceeds maximum daily loss limit of {portfolio.max_daily_loss:.1f}%",
                    "value": pnl_percentage
                })

            if portfolio.max_drawdown:
                # Simplified drawdown check (would need historical data for proper calculation)
                if pnl_percentage <= -portfolio.max_drawdown:
                    alerts.append({
                        "type": "portfolio_drawdown",
                        "severity": "high",
                        "message": f"Portfolio drawdown of {abs(pnl_percentage):.1f}% exceeds maximum drawdown limit of {portfolio.max_drawdown:.1f}%",
                        "value": pnl_percentage
                    })

            # Check position-level alerts
            for pos in positions:
                if pos.market_value and portfolio.total_value > 0:
                    weight = (pos.market_value / portfolio.total_value) * 100

                    if portfolio.max_position_size and weight > portfolio.max_position_size:
                        alerts.append({
                            "type": "position_size",
                            "severity": "medium",
                            "message": f"Position {pos.symbol} weight of {weight:.1f}% exceeds maximum position size limit of {portfolio.max_position_size:.1f}%",
                            "symbol": pos.symbol,
                            "value": weight
                        })

                    # Check for significant P&L changes
                    pnl_pct = (pos.unrealized_pnl / pos.market_value) * 100 if pos.market_value > 0 else 0
                    if abs(pnl_pct) > 10:  # 10% threshold
                        severity = "high" if abs(pnl_pct) > 20 else "medium"
                        alerts.append({
                            "type": "position_pnl",
                            "severity": severity,
                            "message": f"Position {pos.symbol} has {'gained' if pnl_pct > 0 else 'lost'} {abs(pnl_pct):.1f}%",
                            "symbol": pos.symbol,
                            "value": pnl_pct
                        })

            return {
                "alerts": alerts,
                "total_alerts": len(alerts),
                "high_severity": len([a for a in alerts if a["severity"] == "high"]),
                "medium_severity": len([a for a in alerts if a["severity"] == "medium"])
            }

        except Exception as e:
            logger.error(f"Portfolio alerts check failed: {e}")
            return {"error": str(e)}