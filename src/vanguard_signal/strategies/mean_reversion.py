"""
mean_reversion.py — Mean reversion strategy.

A strategy that identifies overbought/oversold conditions and
generates signals to buy low and sell high based on statistical
deviations from the mean.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from .base import BaseStrategy, Signal, SignalType, StrategyConfig, StrategyType


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy.

    Identifies assets that have deviated significantly from their
    historical mean and generates contrarian signals.
    """

    STRATEGY_ID = "mean_reversion"
    STRATEGY_TYPE = StrategyType.MEAN_REVERSION
    VERSION = "1.0.0"
    AUTHOR = "Intel-AI"

    def __init__(self, config: StrategyConfig):
        super().__init__(config)

        # Strategy parameters
        self.lookback_period = config.parameters.get('lookback_period', 20)  # 20-day lookback
        self.entry_threshold = config.parameters.get('entry_threshold', 2.0)  # 2 standard deviations
        self.exit_threshold = config.parameters.get('exit_threshold', 0.5)   # 0.5 standard deviations

    async def generate_signals(
        self,
        market_data,
        portfolio
    ) -> List[Signal]:
        """
        Generate mean reversion signals.

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

                # Calculate z-score (deviation from mean)
                z_score = await self._calculate_z_score(symbol, current_price, market_data)

                if z_score is None:
                    continue

                position = portfolio.get_position(symbol)

                # Check for oversold condition (buy signal)
                if z_score <= -self.entry_threshold:
                    if position is None or position.get('quantity', 0) <= 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.BUY,
                            strength=min(Decimal('1'), abs(z_score) / Decimal('4')),  # Normalize strength
                            price=current_price,
                            metadata={
                                'strategy': 'mean_reversion',
                                'z_score': float(z_score),
                                'lookback_period': self.lookback_period,
                                'reason': f'Oversold (z-score: {z_score:.2f})'
                            }
                        ))

                # Check for overbought condition (sell signal)
                elif z_score >= self.entry_threshold:
                    if position and position.get('quantity', 0) > 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            strength=min(Decimal('1'), z_score / Decimal('4')),  # Normalize strength
                            price=current_price,
                            metadata={
                                'strategy': 'mean_reversion',
                                'z_score': float(z_score),
                                'lookback_period': self.lookback_period,
                                'reason': f'Overbought (z-score: {z_score:.2f})'
                            }
                        ))

                # Check for exit conditions (close positions when reverting to mean)
                elif abs(z_score) <= self.exit_threshold:
                    if position and position.get('quantity', 0) > 0:
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            strength=Decimal('0.5'),  # Moderate strength for exit
                            price=current_price,
                            metadata={
                                'strategy': 'mean_reversion',
                                'z_score': float(z_score),
                                'lookback_period': self.lookback_period,
                                'reason': f'Exit position (z-score: {z_score:.2f})'
                            }
                        ))

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error generating signal for {symbol}: {e}")
                continue

        return signals

    async def _calculate_z_score(
        self,
        symbol: str,
        current_price: Decimal,
        market_data
    ) -> Decimal | None:
        """
        Calculate z-score for current price relative to historical mean.

        Z-score = (current_price - mean) / standard_deviation

        Returns:
            Z-score as Decimal, or None if calculation fails
        """
        try:
            # Get historical prices
            # In a real implementation, this would fetch actual historical data
            historical_prices = await market_data.get_historical_prices(
                symbol, self.lookback_period
            )

            if not historical_prices or len(historical_prices) < self.lookback_period:
                return None

            # Calculate mean
            price_sum = sum(historical_prices)
            mean_price = price_sum / len(historical_prices)

            # Calculate standard deviation
            variance = sum((price - mean_price) ** 2 for price in historical_prices) / len(historical_prices)
            std_dev = variance ** Decimal('0.5')

            if std_dev == 0:
                return Decimal('0')

            # Calculate z-score
            z_score = (current_price - mean_price) / std_dev

            return z_score

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating z-score for {symbol}: {e}")
            return None

    def validate_config(self) -> List[str]:
        """Validate strategy configuration."""
        errors = super().validate_config()

        # Additional validation for mean reversion parameters
        if self.lookback_period < 5:
            errors.append("Lookback period must be at least 5")

        if self.entry_threshold <= 0:
            errors.append("Entry threshold must be positive")

        if self.exit_threshold <= 0:
            errors.append("Exit threshold must be positive")

        if self.exit_threshold >= self.entry_threshold:
            errors.append("Exit threshold must be less than entry threshold")

        return errors