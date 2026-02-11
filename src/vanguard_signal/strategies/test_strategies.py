"""
test_strategies.py — Basic tests for the strategy framework.

Tests strategy loading, instantiation, and basic functionality.
"""

import asyncio
from decimal import Decimal

from .base import SignalType, StrategyConfig, StrategyType
from .registry import StrategyRegistry


class MockMarketData:
    """Mock market data for testing."""

    async def get_price(self, symbol: str) -> Decimal | None:
        # Return mock prices
        prices = {
            'AAPL': Decimal('150.00'),
            'GOOGL': Decimal('2800.00'),
            'MSFT': Decimal('300.00'),
        }
        return prices.get(symbol)

    async def get_historical_prices(self, symbol: str, periods: int) -> list[Decimal]:
        # Return mock historical prices
        base_prices = {
            'AAPL': [Decimal('145.00'), Decimal('148.00'), Decimal('152.00'), Decimal('149.00'), Decimal('150.00')],
            'GOOGL': [Decimal('2750.00'), Decimal('2780.00'), Decimal('2820.00'), Decimal('2790.00'), Decimal('2800.00')],
            'MSFT': [Decimal('295.00'), Decimal('298.00'), Decimal('302.00'), Decimal('299.00'), Decimal('300.00')],
        }
        return base_prices.get(symbol, [])[-periods:]

    async def get_recent_volume(self, symbol: str, periods: int) -> list[int]:
        # Return mock volume data
        volumes = {
            'AAPL': [1000000, 1200000, 1100000, 1300000, 1250000],
            'GOOGL': [500000, 600000, 550000, 650000, 625000],
            'MSFT': [800000, 900000, 850000, 950000, 925000],
        }
        return volumes.get(symbol, [])[-periods:]


class MockPortfolio:
    """Mock portfolio for testing."""

    def __init__(self):
        self.positions = {}

    def get_position(self, symbol: str):
        return self.positions.get(symbol)


async def test_strategy_loading():
    """Test that strategies can be loaded from the registry."""
    print("Testing strategy loading...")

    registry = StrategyRegistry()
    strategies = registry.get_available_strategies()

    print(f"Found {len(strategies)} strategies:")
    for strategy_id in strategies:
        print(f"  - {strategy_id}")

    assert len(strategies) >= 3, f"Expected at least 3 strategies, found {len(strategies)}"
    assert 'moving_average_crossover' in strategies, "Moving average strategy not found"
    assert 'mean_reversion' in strategies, "Mean reversion strategy not found"
    assert 'momentum' in strategies, "Momentum strategy not found"

    print("✓ Strategy loading test passed")


async def test_strategy_instantiation():
    """Test that strategies can be instantiated with valid config."""
    print("\nTesting strategy instantiation...")

    registry = StrategyRegistry()

    # Test moving average strategy
    config = StrategyConfig(
        strategy_id='moving_average_crossover',
        name='Moving Average Crossover',
        symbols=['AAPL', 'GOOGL'],
        parameters={'short_period': 10, 'long_period': 20},
        min_signal_strength=Decimal('0.6')
    )

    strategy = registry.create_strategy('moving_average_crossover', config)
    assert strategy is not None, "Failed to create moving average strategy"
    assert strategy.STRATEGY_ID == 'moving_average_crossover'
    assert strategy.STRATEGY_TYPE == StrategyType.TREND_FOLLOWING

    # Test mean reversion strategy
    config2 = StrategyConfig(
        strategy_id='mean_reversion',
        name='Mean Reversion Strategy',
        symbols=['MSFT'],
        parameters={'lookback_period': 15, 'entry_threshold': 1.5},
        min_signal_strength=Decimal('0.5')
    )

    strategy2 = registry.create_strategy('mean_reversion', config2)
    assert strategy2 is not None, "Failed to create mean reversion strategy"
    assert strategy2.STRATEGY_ID == 'mean_reversion'
    assert strategy2.STRATEGY_TYPE == StrategyType.MEAN_REVERSION

    print("✓ Strategy instantiation test passed")


async def test_signal_generation():
    """Test that strategies can generate signals."""
    print("\nTesting signal generation...")

    registry = StrategyRegistry()
    market_data = MockMarketData()
    portfolio = MockPortfolio()

    # Test moving average strategy
    config = StrategyConfig(
        strategy_id='moving_average_crossover',
        name='Moving Average Crossover',
        symbols=['AAPL'],
        parameters={'short_period': 5, 'long_period': 10},
        min_signal_strength=Decimal('0.1')  # Low threshold for testing
    )

    strategy = registry.create_strategy('moving_average_crossover', config)
    signals = await strategy.generate_signals(market_data, portfolio)

    assert isinstance(signals, list), "Signals should be a list"
    print(f"Generated {len(signals)} signals from moving average strategy")

    # Test mean reversion strategy
    config2 = StrategyConfig(
        strategy_id='mean_reversion',
        name='Mean Reversion Strategy',
        symbols=['GOOGL'],
        parameters={'lookback_period': 5, 'entry_threshold': 1.0},
        min_signal_strength=Decimal('0.1')
    )

    strategy2 = registry.create_strategy('mean_reversion', config2)
    signals2 = await strategy2.generate_signals(market_data, portfolio)

    assert isinstance(signals2, list), "Signals should be a list"
    print(f"Generated {len(signals2)} signals from mean reversion strategy")

    print("✓ Signal generation test passed")


async def test_config_validation():
    """Test strategy configuration validation."""
    print("\nTesting configuration validation...")

    registry = StrategyRegistry()

    # Test invalid config (short period >= long period)
    config = StrategyConfig(
        strategy_id='moving_average_crossover',
        name='Moving Average Crossover',
        symbols=['AAPL'],
        parameters={'short_period': 20, 'long_period': 20},  # Invalid: equal periods
        min_signal_strength=Decimal('0.5')
    )

    strategy = registry.create_strategy('moving_average_crossover', config)
    assert strategy is None, "Should not create strategy with invalid config"

    # Test valid config
    config2 = StrategyConfig(
        strategy_id='moving_average_crossover',
        name='Moving Average Crossover',
        symbols=['AAPL'],
        parameters={'short_period': 10, 'long_period': 20},
        min_signal_strength=Decimal('0.5')
    )

    strategy2 = registry.create_strategy('moving_average_crossover', config2)
    errors2 = strategy2.validate_config()

    assert len(errors2) == 0, f"Valid config should have no errors, but got: {errors2}"
    print("✓ Configuration validation test passed")


async def run_tests():
    """Run all strategy tests."""
    print("Running strategy framework tests...\n")

    try:
        await test_strategy_loading()
        await test_strategy_instantiation()
        await test_signal_generation()
        await test_config_validation()

        print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_tests())