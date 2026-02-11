"""
risk_management.py — Risk management service for position sizing, stop-loss, and safety controls.

Provides comprehensive risk management including:
- Position sizing algorithms (Kelly criterion, fixed percentage)
- Stop-loss and take-profit automation
- Circuit breaker system for extreme conditions
- Maximum drawdown controls
- Portfolio diversification monitoring
- Risk exposure tracking and alerts
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vanguard_signal.schema.models.risk_management import (
    RiskProfile,
    PositionSizeRule,
    StopLossRule,
    CircuitBreaker,
    RiskAlert,
    UserRiskMetrics,
    DrawdownLimit,
    DiversificationRule,
)
from vanguard_signal.schema.models.trading import Portfolio, Position, Order
from vanguard_signal.market_data import MarketDataService

logger = logging.getLogger(__name__)


class RiskManagementService:
    """Comprehensive risk management service for trading operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data = MarketDataService(db)

    async def get_or_create_risk_profile(self, user_id: UUID) -> RiskProfile:
        """Get existing risk profile or create default one for user."""
        result = await self.db.execute(
            select(RiskProfile).where(RiskProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            profile = RiskProfile(
                user_id=user_id,
                risk_tolerance="moderate",
                max_portfolio_risk=0.02,  # 2%
                max_single_position_risk=0.01,  # 1%
                max_daily_loss=0.05,  # 5%
                max_drawdown=0.10,  # 10%
                position_sizing_method="fixed_percentage",
                base_position_size=0.02,  # 2%
                kelly_fraction=0.5,
                max_sector_exposure=0.25,  # 25%
                max_single_stock_exposure=0.05,  # 5%
                min_diversification_stocks=5,
                use_stop_loss=True,
                default_stop_loss_pct=0.05,  # 5%
                trailing_stop_enabled=False,
                circuit_breaker_enabled=True,
                volatility_threshold=0.03,  # 3%
                market_drop_threshold=0.05,  # 5%
                email_alerts_enabled=True,
                sms_alerts_enabled=False,
                is_active=True,
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        return profile

    async def calculate_position_size(
        self,
        user_id: UUID,
        symbol: str,
        entry_price: Decimal,
        stop_loss_price: Optional[Decimal] = None,
        portfolio_value: Optional[Decimal] = None,
        win_probability: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate appropriate position size based on risk profile and parameters.

        Args:
            user_id: User ID
            symbol: Stock symbol
            entry_price: Entry price
            stop_loss_price: Stop loss price (if known)
            portfolio_value: Current portfolio value
            win_probability: Estimated win probability (for Kelly)
            win_loss_ratio: Estimated win/loss ratio (for Kelly)

        Returns:
            Dict with position size details
        """
        profile = await self.get_or_create_risk_profile(user_id)

        if portfolio_value is None:
            # Get current portfolio value
            portfolio_result = await self.db.execute(
                select(Portfolio).where(Portfolio.user_id == user_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            portfolio_value = portfolio.current_balance if portfolio else Decimal("100000")

        # Calculate risk per trade
        risk_per_trade = float(portfolio_value) * profile.max_single_position_risk

        # Calculate stop loss distance if not provided
        if stop_loss_price is None:
            stop_loss_distance = float(entry_price) * profile.default_stop_loss_pct
        else:
            stop_loss_distance = abs(float(entry_price) - float(stop_loss_price))

        # Base position size calculation
        if profile.position_sizing_method == "fixed_percentage":
            base_size = float(portfolio_value) * profile.base_position_size
        elif profile.position_sizing_method == "kelly_criterion" and win_probability and win_loss_ratio:
            # Kelly formula: f = (bp - q) / b
            # where: b = odds (win_loss_ratio), p = win probability, q = loss probability
            kelly_fraction = (win_probability * win_loss_ratio - (1 - win_probability)) / win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            kelly_fraction *= profile.kelly_fraction  # Apply user's Kelly fraction
            base_size = float(portfolio_value) * kelly_fraction
        elif profile.position_sizing_method == "equal_risk":
            base_size = risk_per_trade / stop_loss_distance if stop_loss_distance > 0 else 0
        else:
            base_size = float(portfolio_value) * profile.base_position_size

        # Apply risk-based adjustments
        max_risk_based_size = risk_per_trade / stop_loss_distance if stop_loss_distance > 0 else base_size
        position_size = min(base_size, max_risk_based_size)

        # Check diversification limits
        diversification_check = await self.check_diversification_limits(user_id, symbol, position_size, portfolio_value)
        if not diversification_check["compliant"]:
            position_size *= diversification_check["adjustment_factor"]

        # Convert to number of shares
        shares = int(position_size / float(entry_price))

        # Ensure minimum position size
        if shares < 1:
            shares = 1

        total_value = shares * float(entry_price)
        risk_amount = shares * stop_loss_distance

        return {
            "shares": shares,
            "total_value": total_value,
            "risk_amount": risk_amount,
            "risk_percentage": (risk_amount / float(portfolio_value)) * 100,
            "method_used": profile.position_sizing_method,
            "diversification_compliant": diversification_check["compliant"],
            "warnings": diversification_check.get("warnings", []),
        }

    async def check_diversification_limits(
        self, user_id: UUID, symbol: str, position_value: float, portfolio_value: Decimal
    ) -> Dict[str, Any]:
        """Check if adding position would violate diversification limits."""
        profile = await self.get_or_create_risk_profile(user_id)

        # Get current positions
        positions_result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.quantity > 0
                )
            )
        )
        positions = positions_result.scalars().all()

        # Calculate current exposures
        current_exposures = {}
        total_value = float(portfolio_value)

        for pos in positions:
            if pos.market_value:
                exposure = float(pos.market_value) / total_value
                current_exposures[pos.symbol] = exposure

        # Check single stock limit
        new_exposure = position_value / total_value
        existing_exposure = current_exposures.get(symbol, 0)
        total_exposure = existing_exposure + new_exposure

        warnings = []
        compliant = True
        adjustment_factor = 1.0

        if total_exposure > profile.max_single_stock_exposure:
            compliant = False
            max_allowed = profile.max_single_stock_exposure - existing_exposure
            if max_allowed > 0:
                adjustment_factor = max_allowed / new_exposure
            else:
                adjustment_factor = 0
            warnings.append(f"Single stock exposure would exceed {profile.max_single_stock_exposure:.1%} limit")

        # Check minimum diversification
        if len(positions) + 1 < profile.min_diversification_stocks:
            warnings.append(f"Portfolio would have fewer than {profile.min_diversification_stocks} positions")

        return {
            "compliant": compliant,
            "adjustment_factor": adjustment_factor,
            "warnings": warnings,
            "current_exposure": total_exposure,
            "max_allowed": profile.max_single_stock_exposure,
        }

    async def check_stop_loss_triggers(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Check all positions for stop-loss triggers."""
        # Get user positions
        positions_result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.quantity > 0
                )
            )
        )
        positions = positions_result.scalars().all()

        triggers = []

        for position in positions:
            if not position.current_price:
                continue

            # Get stop-loss rules for this user
            rules_result = await self.db.execute(
                select(StopLossRule).where(
                    and_(
                        StopLossRule.user_id == user_id,
                        StopLossRule.is_active == True
                    )
                )
            )
            rules = rules_result.scalars().all()

            for rule in rules:
                trigger_price = self._calculate_stop_price(position, rule)

                if trigger_price and self._should_trigger_stop(position, trigger_price, rule):
                    triggers.append({
                        "position_id": position.id,
                        "symbol": position.symbol,
                        "current_price": float(position.current_price),
                        "trigger_price": trigger_price,
                        "rule_name": rule.name,
                        "action": "stop_loss",
                        "quantity": float(position.quantity),
                    })

        return triggers

    def _calculate_stop_price(self, position: Position, rule: StopLossRule) -> Optional[float]:
        """Calculate stop price based on rule type."""
        if not position.average_cost or not position.current_price:
            return None

        entry_price = float(position.average_cost)

        if rule.stop_loss_type == "percentage":
            if position.is_long:
                return entry_price * (1 - rule.stop_loss_value)
            else:
                return entry_price * (1 + rule.stop_loss_value)
        elif rule.stop_loss_type == "fixed":
            if position.is_long:
                return entry_price - rule.stop_loss_value
            else:
                return entry_price + rule.stop_loss_value
        elif rule.stop_loss_type == "trailing" and rule.trailing_stop_enabled:
            # For trailing stops, we'd need to track the highest price since entry
            # This is a simplified implementation
            if position.is_long:
                return float(position.current_price) * (1 - rule.trailing_stop_distance)
            else:
                return float(position.current_price) * (1 + rule.trailing_stop_distance)

        return None

    def _should_trigger_stop(
        self, position: Position, trigger_price: float, rule: StopLossRule
    ) -> bool:
        """Check if stop-loss should be triggered."""
        if not position.current_price:
            return False

        current_price = float(position.current_price)

        if position.is_long:
            return current_price <= trigger_price
        else:
            return current_price >= trigger_price

    async def check_circuit_breakers(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Check all circuit breaker conditions."""
        breakers_result = await self.db.execute(
            select(CircuitBreaker).where(
                and_(
                    CircuitBreaker.user_id == user_id,
                    CircuitBreaker.is_active == True
                )
            )
        )
        breakers = breakers_result.scalars().all()

        triggered_breakers = []

        for breaker in breakers:
            if await self._evaluate_circuit_breaker(breaker):
                triggered_breakers.append({
                    "breaker_id": breaker.id,
                    "name": breaker.name,
                    "trigger_type": breaker.trigger_type,
                    "action_type": breaker.action_type,
                    "triggered_at": datetime.now(timezone.utc),
                })

                # Update breaker status
                breaker.is_triggered = True
                breaker.triggered_at = datetime.now(timezone.utc)
                breaker.trigger_count += 1

        if triggered_breakers:
            await self.db.commit()

        return triggered_breakers

    async def _evaluate_circuit_breaker(self, breaker: CircuitBreaker) -> bool:
        """Evaluate if a circuit breaker should be triggered."""
        if breaker.trigger_type == "volatility":
            # Check portfolio volatility
            volatility = await self._calculate_portfolio_volatility(breaker.user_id)
            return volatility >= breaker.trigger_threshold

        elif breaker.trigger_type == "drawdown":
            # Check drawdown
            drawdown = await self._calculate_current_drawdown(breaker.user_id)
            return drawdown >= breaker.trigger_threshold

        elif breaker.trigger_type == "market_drop":
            # Check market performance
            market_return = await self._calculate_market_return(breaker.trigger_timeframe)
            return market_return <= -breaker.trigger_threshold

        return False

    async def _calculate_portfolio_volatility(self, user_id: UUID) -> float:
        """Calculate current portfolio volatility."""
        # Get recent portfolio values (simplified implementation)
        metrics_result = await self.db.execute(
            select(UserRiskMetrics).where(UserRiskMetrics.user_id == user_id)
            .order_by(desc(UserRiskMetrics.timestamp))
            .limit(30)  # Last 30 data points
        )
        metrics = metrics_result.scalars().all()

        if len(metrics) < 2:
            return 0.0

        returns = []
        for i in range(1, len(metrics)):
            if metrics[i-1].portfolio_value > 0:
                ret = float(metrics[i].portfolio_value - metrics[i-1].portfolio_value) / float(metrics[i-1].portfolio_value)
                returns.append(ret)

        return np.std(returns) * np.sqrt(252) if returns else 0.0  # Annualized

    async def _calculate_current_drawdown(self, user_id: UUID) -> float:
        """Calculate current portfolio drawdown."""
        metrics_result = await self.db.execute(
            select(UserRiskMetrics).where(UserRiskMetrics.user_id == user_id)
            .order_by(desc(UserRiskMetrics.timestamp))
            .limit(1)
        )
        latest_metric = metrics_result.scalar_one_or_none()

        if not latest_metric:
            return 0.0

        return latest_metric.current_drawdown

    async def _calculate_market_return(self, timeframe: str) -> float:
        """Calculate market return over specified timeframe."""
        # Simplified implementation - would use actual market data
        # For now, return a mock value
        return 0.02  # 2% return

    async def update_risk_metrics(self, user_id: UUID) -> UserRiskMetrics:
        """Update and return current risk metrics for user."""
        # Get current portfolio
        portfolio_result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            raise ValueError("Portfolio not found")

        # Get positions
        positions_result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.quantity > 0
                )
            )
        )
        positions = positions_result.scalars().all()

        # Calculate metrics
        portfolio_value = portfolio.current_balance
        position_values = []

        for pos in positions:
            if pos.market_value:
                position_values.append(float(pos.market_value))
                portfolio_value += pos.market_value

        # Calculate diversification metrics
        stock_count = len(positions)
        largest_position = max(position_values) if position_values else 0
        largest_position_pct = (largest_position / float(portfolio_value)) if portfolio_value > 0 else 0

        # Get historical metrics for volatility calculation
        historical_result = await self.db.execute(
            select(UserRiskMetrics).where(UserRiskMetrics.user_id == user_id)
            .order_by(desc(UserRiskMetrics.timestamp))
            .limit(30)
        )
        historical = historical_result.scalars().all()

        # Calculate volatility
        volatility = 0.0
        if len(historical) >= 2:
            returns = []
            for i in range(1, len(historical)):
                prev_val = float(historical[i-1].portfolio_value)
                curr_val = float(historical[i].portfolio_value)
                if prev_val > 0:
                    ret = (curr_val - prev_val) / prev_val
                    returns.append(ret)
            volatility = np.std(returns) * np.sqrt(252) if returns else 0.0

        # Create metrics record
        metrics = UserRiskMetrics(
            user_id=user_id,
            portfolio_value=portfolio_value,
            portfolio_risk=largest_position_pct,  # Simplified
            stock_count=stock_count,
            largest_position_pct=largest_position_pct,
            portfolio_volatility=volatility,
        )

        self.db.add(metrics)
        await self.db.commit()
        await self.db.refresh(metrics)

        return metrics

    async def create_risk_alert(
        self,
        user_id: UUID,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        trigger_value: float,
        threshold_value: float,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> RiskAlert:
        """Create a risk alert."""
        profile = await self.get_or_create_risk_profile(user_id)

        alert = RiskAlert(
            user_id=user_id,
            profile_id=profile.id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            trigger_value=trigger_value,
            threshold_value=threshold_value,
            context_data=context_data or {},
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        # TODO: Send notifications (email, SMS)

        return alert

    async def check_all_risk_limits(self, user_id: UUID) -> List[RiskAlert]:
        """Check all risk limits and create alerts for violations."""
        alerts = []

        # Check drawdown limits
        drawdown_alerts = await self._check_drawdown_limits(user_id)
        alerts.extend(drawdown_alerts)

        # Check diversification
        diversification_alerts = await self._check_diversification_limits(user_id)
        alerts.extend(diversification_alerts)

        # Check position concentration
        concentration_alerts = await self._check_position_concentration(user_id)
        alerts.extend(concentration_alerts)

        return alerts

    async def _check_drawdown_limits(self, user_id: UUID) -> List[RiskAlert]:
        """Check drawdown limits and create alerts."""
        alerts = []

        limits_result = await self.db.execute(
            select(DrawdownLimit).where(
                and_(
                    DrawdownLimit.user_id == user_id,
                    DrawdownLimit.is_active == True
                )
            )
        )
        limits = limits_result.scalars().all()

        current_drawdown = await self._calculate_current_drawdown(user_id)

        for limit in limits:
            if current_drawdown >= limit.max_drawdown_pct and not limit.is_breached:
                alert = await self.create_risk_alert(
                    user_id=user_id,
                    alert_type="drawdown",
                    severity="high",
                    title=f"Drawdown Limit Breached: {limit.name}",
                    message=f"Portfolio drawdown of {current_drawdown:.1%} exceeds limit of {limit.max_drawdown_pct:.1%}",
                    trigger_value=current_drawdown,
                    threshold_value=limit.max_drawdown_pct,
                    context_data={"limit_id": str(limit.id), "limit_name": limit.name},
                )
                alerts.append(alert)

                # Update limit status
                limit.is_breached = True
                limit.breached_at = datetime.now(timezone.utc)
                limit.breach_count += 1

        await self.db.commit()
        return alerts

    async def _check_diversification_limits(self, user_id: UUID) -> List[RiskAlert]:
        """Check diversification requirements."""
        alerts = []

        rules_result = await self.db.execute(
            select(DiversificationRule).where(
                and_(
                    DiversificationRule.user_id == user_id,
                    DiversificationRule.is_active == True
                )
            )
        )
        rules = rules_result.scalars().all()

        for rule in rules:
            compliance = await self._calculate_diversification_compliance(user_id, rule)

            if not compliance["compliant"] and rule.is_compliant:
                alert = await self.create_risk_alert(
                    user_id=user_id,
                    alert_type="diversification",
                    severity="medium",
                    title=f"Diversification Rule Violated: {rule.name}",
                    message=f"Portfolio no longer meets diversification requirements. Compliance score: {compliance['score']:.2f}",
                    trigger_value=compliance["score"],
                    threshold_value=0.8,  # 80% compliance threshold
                    context_data={"rule_id": str(rule.id), "violations": compliance["violations"]},
                )
                alerts.append(alert)

                # Update rule status
                rule.is_compliant = False
                rule.violation_count += 1
                rule.last_violation = datetime.now(timezone.utc)

        await self.db.commit()
        return alerts

    async def _calculate_diversification_compliance(
        self, user_id: UUID, rule: DiversificationRule
    ) -> Dict[str, Any]:
        """Calculate diversification compliance score."""
        # Get positions
        positions_result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.quantity > 0
                )
            )
        )
        positions = positions_result.scalars().all()

        if len(positions) < rule.min_stocks:
            return {
                "compliant": False,
                "score": 0.0,
                "violations": [f"Minimum {rule.min_stocks} stocks required, only {len(positions)} found"],
            }

        # Calculate weights (simplified - would need sector/industry data)
        total_value = sum(float(p.market_value or 0) for p in positions)
        if total_value == 0:
            return {"compliant": False, "score": 0.0, "violations": ["No portfolio value"]}

        violations = []
        score = 1.0

        # Check stock weights
        for pos in positions:
            weight = float(pos.market_value or 0) / total_value
            if weight > rule.max_stock_weight:
                violations.append(f"{pos.symbol} weight {weight:.1%} exceeds limit {rule.max_stock_weight:.1%}")
                score *= 0.9  # Penalty for violations

        # Simplified compliance score
        score = max(0.0, min(1.0, score))

        return {
            "compliant": len(violations) == 0,
            "score": score,
            "violations": violations,
        }

    async def _check_position_concentration(self, user_id: UUID) -> List[RiskAlert]:
        """Check position concentration limits."""
        alerts = []

        profile = await self.get_or_create_risk_profile(user_id)

        # Get positions
        positions_result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.quantity > 0
                )
            )
        )
        positions = positions_result.scalars().all()

        # Get portfolio value
        portfolio_result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio or not positions:
            return alerts

        total_value = float(portfolio.current_balance)
        for pos in positions:
            if pos.market_value:
                total_value += float(pos.market_value)

        # Check largest position
        largest_position = max((float(p.market_value or 0) for p in positions), default=0)
        largest_pct = largest_position / total_value if total_value > 0 else 0

        if largest_pct > profile.max_single_stock_exposure:
            alert = await self.create_risk_alert(
                user_id=user_id,
                alert_type="concentration",
                severity="medium",
                title="Position Concentration Warning",
                message=f"Largest position represents {largest_pct:.1%} of portfolio, exceeding limit of {profile.max_single_stock_exposure:.1%}",
                trigger_value=largest_pct,
                threshold_value=profile.max_single_stock_exposure,
            )
            alerts.append(alert)

        return alerts