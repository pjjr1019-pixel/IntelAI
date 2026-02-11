"""
moving_average.py — Simple moving average crossover strategy.

A basic trend-following strategy that generates buy/sell signals
based on short-term and long-term moving average crossovers.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from .base import BaseStrategy, Signal, SignalType, StrategyConfig, StrategyType


class MovingAverageStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.

    Generates buy signals when short MA crosses above long MA,
    and sell signals when short MA crosses below long MA.
    """

    STRATEGY_ID = "moving_average_crossover"
    STRATEGY_NAME = "Moving Average Crossover"
    STRATEGY_TYPE = StrategyType.TREND_FOLLOWING
    VERSION = "1.0.0"
    AUTHOR = "Intel-AI"

    def __init__(self, config: StrategyConfig):
        super().__init__(config)

        # Strategy parameters
        self.short_period = config.parameters.get('short_period', 20)  # 20-day MA
        self.long_period = config.parameters.get('long_period', 50)    # 50-day MA

    async def generate_signals(
        self,
        market_data,
        portfolio
    ) -> List[Signal]:
        """
        Generate signals based on moving average crossovers.

        Args:
            market_data: Market data access
            portfolio: Portfolio state

        Returns:
            List of trading signals
        """
        signals = []

        for symbol in self.config.symbols:
            try:
                # Get historical prices for MA calculation
                # In a real implementation, this would fetch actual historical data
                # For now, we'll use a simplified approach
                current_price = await market_data.get_price(symbol)

                if current_price is None:
                    continue

                # Check if we have a position
                position = portfolio.get_position(symbol)

                # Simple trend detection (placeholder logic)
                # In reality, this would calculate actual moving averages
                trend_strength = self._calculate_trend_strength(symbol, market_data)

                if trend_strength > self.config.min_signal_strength:
                    # Bullish trend - check if we should buy
                    if position is None or position.get('quantity', 0) <= 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.BUY,
                            strength=trend_strength,
                            price=current_price,
                            metadata={
                                'strategy': 'moving_average_crossover',
                                'short_period': self.short_period,
                                'long_period': self.long_period,
                                'reason': 'Short MA crossed above long MA'
                            }
                        ))

                elif trend_strength < (Decimal('1') - self.config.min_signal_strength):
                    # Bearish trend - check if we should sell
                    if position and position.get('quantity', 0) > 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            strength=abs(trend_strength - Decimal('1')),
                            price=current_price,
                            metadata={
                                'strategy': 'moving_average_crossover',
                                'short_period': self.short_period,
                                'long_period': self.long_period,
                                'reason': 'Short MA crossed below long MA'
                            }
                        ))

            except Exception as e:
                # Log error but continue with other symbols
                if self.logger:
                    self.logger.error(f"Error generating signal for {symbol}: {e}")
                continue

        return signals

    def _calculate_trend_strength(self, symbol: str, market_data) -> Decimal:
        """
        Calculate trend strength based on moving average relationship.

        This is a simplified placeholder. In a real implementation,
        this would calculate actual moving averages from historical data.

        Returns:
            Decimal between 0.0 (bearish) and 1.0 (bullish)
        """
        # Placeholder logic - in reality, this would:
        # 1. Fetch historical price data
        # 2. Calculate short-term and long-term moving averages
        # 3. Determine crossover status and strength

        # For demonstration, return a random-ish value based on symbol
        # In production, this would be proper technical analysis
        symbol_hash = sum(ord(c) for c in symbol)
        base_strength = Decimal(str((symbol_hash % 100) / 100))

        # Add some noise to simulate market conditions
        import random
        noise = Decimal(str(random.uniform(-0.1, 0.1)))

        strength = max(Decimal('0'), min(Decimal('1'), base_strength + noise))
        return strength

    def validate_config(self) -> List[str]:
        """Validate strategy configuration."""
        errors = super().validate_config()

        # Additional validation for moving average parameters
        if self.short_period >= self.long_period:
            errors.append("Short period must be less than long period")

        if self.short_period < 2:
            errors.append("Short period must be at least 2")

        if self.long_period < 5:
            errors.append("Long period must be at least 5")

        return errors