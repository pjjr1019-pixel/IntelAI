# Trading Strategies Framework

This package provides a comprehensive framework for implementing, testing, and deploying trading strategies in the Intel-AI system.

## Overview

The strategy framework consists of:

- **Base Classes**: Abstract base classes defining the strategy interface
- **Registry System**: Automatic discovery and management of strategies
- **Data Structures**: Type-safe dataclasses for configuration and signals
- **Concrete Strategies**: Ready-to-use trading strategy implementations

## Architecture

### Core Components

#### BaseStrategy
Abstract base class that all trading strategies must inherit from. Defines the interface for:
- Signal generation (`generate_signals()`)
- Configuration validation (`validate_config()`)
- Parameter management

#### StrategyRegistry
Central registry for strategy discovery and instantiation:
- Automatic discovery of strategy classes from the package
- Factory pattern for strategy creation
- Strategy metadata management

#### StrategyConfig
Configuration dataclass containing:
- Strategy identification (ID, name, description)
- Trading parameters (symbols, risk limits, thresholds)
- Strategy-specific parameters

#### Signal & StrategyResult
Data structures for:
- Trading signals (BUY/SELL/HOLD/CLOSE)
- Strategy execution results and metadata

## Available Strategies

### Moving Average Crossover (`moving_average_crossover`)
**Type**: Trend Following

Generates buy signals when short-term MA crosses above long-term MA, and sell signals when short-term MA crosses below long-term MA.

**Parameters**:
- `short_period`: Short-term moving average period (default: 20)
- `long_period`: Long-term moving average period (default: 50)

### Mean Reversion (`mean_reversion`)
**Type**: Mean Reversion

Identifies overbought/oversold conditions based on statistical deviations from historical mean and generates contrarian signals.

**Parameters**:
- `lookback_period`: Historical lookback period for mean calculation (default: 20)
- `entry_threshold`: Standard deviation threshold for entry signals (default: 2.0)
- `exit_threshold`: Standard deviation threshold for exit signals (default: 0.5)

### Momentum (`momentum`)
**Type**: Momentum

Identifies assets with strong recent performance and generates signals to capitalize on continued momentum trends.

**Parameters**:
- `momentum_period`: Period for momentum calculation (default: 20)
- `volume_threshold`: Volume confirmation threshold multiplier (default: 1.5)
- `min_momentum`: Minimum momentum threshold (default: 0.05)

## Usage

### Basic Usage

```python
from vanguard_signal.strategies import StrategyRegistry, StrategyConfig
from decimal import Decimal

# Create registry (automatically discovers strategies)
registry = StrategyRegistry()

# List available strategies
strategies = registry.get_available_strategies()
print("Available strategies:", strategies)

# Create strategy configuration
config = StrategyConfig(
    strategy_id='moving_average_crossover',
    name='My MA Strategy',
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    parameters={
        'short_period': 10,
        'long_period': 20
    },
    min_signal_strength=Decimal('0.7'),
    max_position_size=Decimal('0.1')
)

# Instantiate strategy
strategy = registry.create_strategy('moving_average_crossover', config)

# Generate signals (requires market_data and portfolio interfaces)
signals = await strategy.generate_signals(market_data, portfolio)
```

### Implementing Custom Strategies

```python
from vanguard_signal.strategies import BaseStrategy, Signal, SignalType, StrategyConfig, StrategyType

class MyCustomStrategy(BaseStrategy):
    STRATEGY_ID = "my_custom_strategy"
    STRATEGY_TYPE = StrategyType.TREND_FOLLOWING
    VERSION = "1.0.0"
    AUTHOR = "Your Name"

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        # Initialize strategy-specific parameters
        self.my_parameter = config.parameters.get('my_parameter', 'default_value')

    async def generate_signals(self, market_data, portfolio):
        """Implement your signal generation logic here."""
        signals = []

        for symbol in self.config.symbols:
            # Your strategy logic here
            # Access market data: await market_data.get_price(symbol)
            # Check portfolio: portfolio.get_position(symbol)

            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=Decimal('0.8'),
                price=current_price,
                metadata={'reason': 'Custom logic triggered'}
            ))

        return signals

    def validate_config(self):
        """Validate strategy configuration."""
        errors = super().validate_config()
        # Add custom validation logic
        if self.my_parameter < 0:
            errors.append("my_parameter must be non-negative")
        return errors
```

### Strategy Types

- `TREND_FOLLOWING`: Strategies that follow market trends
- `MEAN_REVERSION`: Strategies that bet on price returning to mean
- `MOMENTUM`: Strategies that ride momentum trends
- `ARBITRAGE`: Statistical or triangular arbitrage strategies
- `BREAKOUT`: Strategies based on price breakouts
- `PORTFOLIO`: Multi-asset portfolio allocation strategies
- `MACHINE_LEARNING`: ML-based prediction strategies

## Testing

Run the strategy tests:

```bash
cd src
python -m vanguard_signal.strategies.test_strategies
```

## Integration

The strategy framework integrates with:

- **Market Data Service**: Provides price and historical data
- **Portfolio Management**: Tracks positions and risk
- **Risk Management**: Validates position sizes and drawdowns
- **Backtesting Engine**: Tests strategies on historical data
- **Live Trading Engine**: Executes strategies in real-time

## Next Steps

1. **Backtesting Engine**: Implement walk-forward analysis and performance metrics
2. **Strategy Optimization**: Parameter optimization and walk-forward validation
3. **Risk Management**: Strategy-level risk controls and position sizing
4. **Portfolio Integration**: Multi-strategy portfolio allocation
5. **Live Deployment**: Strategy deployment and monitoring tools</content>
<parameter name="filePath">c:\Users\Pgiov\OneDrive\Documents\Custom programs\Intel-AI\src\vanguard_signal\strategies\README.md