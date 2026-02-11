"""
momentum.py — Momentum-based trading strategy.

A strategy that identifies assets with strong recent performance
and generates signals to ride the momentum trend.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from .base import BaseStrategy, Signal, SignalType, StrategyConfig, StrategyType


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy.

    Identifies assets with strong recent performance and generates
    signals to capitalize on continued momentum.
    """

    STRATEGY_ID = "momentum"
    STRATEGY_TYPE = StrategyType.MOMENTUM
    VERSION = "1.0.0"
    AUTHOR = "Intel-AI"

    def __init__(self, config: StrategyConfig):
        super().__init__(config)

        # Strategy parameters
        self.momentum_period = config.parameters.get('momentum_period', 20)  # 20-day momentum
        self.volume_threshold = config.parameters.get('volume_threshold', 1.5)  # 1.5x average volume
        self.min_momentum = config.parameters.get('min_momentum', 0.05)  # 5% minimum momentum

    async def generate_signals(
        self,
        market_data,
        portfolio
    ) -> List[Signal]:
        """
        Generate momentum-based signals.

        Args:
            market_data: Market data access
            portfolio: Portfolio state

        Returns:
            List of trading signals
        """
        signals = []

        for symbol in self.config.symbols:
            try:
                current_price = await market_data.get_price(symbol)

                if current_price is None:
                    continue

                # Calculate momentum score
                momentum_score = await self._calculate_momentum_score(symbol, market_data)

                if momentum_score is None:
                    continue

                # Check volume confirmation
                volume_confirmed = await self._check_volume_confirmation(symbol, market_data)

                position = portfolio.get_position(symbol)

                # Strong positive momentum - buy signal
                if momentum_score >= self.min_momentum and volume_confirmed:
                    if position is None or position.get('quantity', 0) <= 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.BUY,
                            strength=min(Decimal('1'), momentum_score * Decimal('2')),  # Amplify strong signals
                            price=current_price,
                            metadata={
                                'strategy': 'momentum',
                                'momentum_score': float(momentum_score),
                                'momentum_period': self.momentum_period,
                                'volume_confirmed': volume_confirmed,
                                'reason': f'Strong momentum ({momentum_score:.1%})'
                            }
                        ))

                # Weak or negative momentum - sell signal
                elif momentum_score <= -self.min_momentum:
                    if position and position.get('quantity', 0) > 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            strength=min(Decimal('1'), abs(momentum_score) * Decimal('2')),
                            price=current_price,
                            metadata={
                                'strategy': 'momentum',
                                'momentum_score': float(momentum_score),
                                'momentum_period': self.momentum_period,
                                'reason': f'Weak momentum ({momentum_score:.1%})'
                            }
                        ))

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error generating signal for {symbol}: {e}")
                continue

        return signals

    async def _calculate_momentum_score(
        self,
        symbol: str,
        market_data
    ) -> Decimal | None:
        """
        Calculate momentum score based on recent price performance.

        Momentum = (current_price - price_n_periods_ago) / price_n_periods_ago

        Returns:
            Momentum score as Decimal, or None if calculation fails
        """
        try:
            # Get historical prices
            historical_prices = await market_data.get_historical_prices(
                symbol, self.momentum_period + 1  # Need one extra for comparison
            )

            if not historical_prices or len(historical_prices) < self.momentum_period + 1:
                return None

            # Calculate momentum
            current_price = historical_prices[-1]
            past_price = historical_prices[0]  # Price from n periods ago

            if past_price == 0:
                return Decimal('0')

            momentum = (current_price - past_price) / past_price

            return momentum

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating momentum for {symbol}: {e}")
            return None

    async def _check_volume_confirmation(
        self,
        symbol: str,
        market_data
    ) -> bool:
        """
        Check if recent volume supports the momentum signal.

        Returns:
            True if volume confirms the momentum, False otherwise
        """
        try:
            # Get recent volume data
            recent_volume = await market_data.get_recent_volume(symbol, 5)  # Last 5 periods

            if not recent_volume:
                return False

            # Calculate average volume
            avg_volume = sum(recent_volume) / len(recent_volume)

            # Check if recent volume exceeds threshold
            current_volume = recent_volume[-1]

            return current_volume >= (avg_volume * self.volume_threshold)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking volume for {symbol}: {e}")
            return False

    def validate_config(self) -> List[str]:
        """Validate strategy configuration."""
        errors = super().validate_config()

        # Additional validation for momentum parameters
        if self.momentum_period < 5:
            errors.append("Momentum period must be at least 5")

        if self.volume_threshold <= 1.0:
            errors.append("Volume threshold must be greater than 1.0")

        if self.min_momentum <= 0:
            errors.append("Minimum momentum must be positive")

        return errors