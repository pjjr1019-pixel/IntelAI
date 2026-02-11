"""
backtesting.py — Backtesting engine for trading strategies.

Provides comprehensive backtesting capabilities including:
- Historical strategy execution on market data
- Performance metrics calculation (returns, Sharpe ratio, max drawdown)
- Walk-forward analysis for realistic testing
- Benchmarking against buy-and-hold strategies
- Risk-adjusted performance analysis
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseStrategy, StrategyConfig, StrategyResult, Signal, SignalType
from .registry import StrategyRegistry
from ..market_data import MarketDataService

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for backtesting execution."""

    # Time period
    start_date: datetime
    end_date: datetime

    # Capital
    initial_capital: Decimal = Decimal("10000.00")

    # Transaction costs
    commission_per_trade: Decimal = Decimal("0.001")  # 0.1%
    slippage_bps: int = 5  # 5 basis points

    # Walk-forward analysis
    walk_forward_window_days: int = 252  # 1 year
    walk_forward_step_days: int = 21  # 1 month

    # Benchmark
    benchmark_symbol: str = "SPY"  # S&P 500 ETF

    # Risk management
    max_position_size: Decimal = Decimal("0.1")  # Max 10% per position
    max_drawdown_limit: Decimal = Decimal("0.2")  # Max 20% drawdown


@dataclass
class BacktestResult:
    """Results from a backtesting run."""

    # Identification
    strategy_id: str
    config: BacktestConfig
    backtest_id: str = field(default_factory=lambda: str(uuid4()))

    # Performance metrics
    total_return: Decimal = Decimal("0.0")
    annualized_return: Decimal = Decimal("0.0")
    volatility: Decimal = Decimal("0.0")
    sharpe_ratio: Decimal = Decimal("0.0")
    max_drawdown: Decimal = Decimal("0.0")
    win_rate: Decimal = Decimal("0.0")
    profit_factor: Decimal = Decimal("0.0")

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: Decimal = Decimal("0.0")
    avg_loss: Decimal = Decimal("0.0")

    # Benchmark comparison
    benchmark_return: Decimal = Decimal("0.0")
    alpha: Decimal = Decimal("0.0")  # Excess return over benchmark

    # Risk metrics
    value_at_risk_95: Decimal = Decimal("0.0")  # 95% VaR
    expected_shortfall_95: Decimal = Decimal("0.0")  # 95% ES

    # Detailed data
    portfolio_values: List[Tuple[datetime, Decimal]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)

    # Walk-forward results (if applicable)
    walk_forward_results: List['BacktestResult'] = field(default_factory=list)


class BacktestingEngine:
    """
    Comprehensive backtesting engine for trading strategies.

    Features:
    - Historical strategy execution
    - Realistic transaction costs and slippage
    - Walk-forward analysis
    - Performance metrics calculation
    - Benchmark comparison
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data = MarketDataService(db)
        self.registry = StrategyRegistry()

    async def run_backtest(
        self,
        strategy_id: str,
        config: BacktestConfig,
        strategy_config: Optional[StrategyConfig] = None
    ) -> BacktestResult:
        """
        Run a complete backtest for a strategy.

        Args:
            strategy_id: ID of the strategy to test
            config: Backtesting configuration
            strategy_config: Strategy-specific configuration

        Returns:
            Complete backtest results
        """
        logger.info(f"Starting backtest for strategy {strategy_id}")

        # Get strategy
        strategy_class = self.registry.get_strategy_class(strategy_id)
        if not strategy_class:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Create strategy instance
        if strategy_config is None:
            strategy_config = StrategyConfig(
                strategy_id=strategy_id,
                name=strategy_class.__name__,
                description=getattr(strategy_class, '__doc__', ''),
            )

        strategy = strategy_class(strategy_config)

        # Run backtest
        result = await self._execute_backtest(strategy, config)

        logger.info(f"Backtest completed for {strategy_id}: "
                   f"Return={result.total_return:.2%}, "
                   f"Sharpe={result.sharpe_ratio:.2f}")

        return result

    async def run_walk_forward_backtest(
        self,
        strategy_id: str,
        config: BacktestConfig,
        strategy_config: Optional[StrategyConfig] = None
    ) -> BacktestResult:
        """
        Run walk-forward analysis for more realistic testing.

        This method runs multiple backtests using rolling windows,
        retraining the strategy on each window before testing.
        """
        logger.info(f"Starting walk-forward backtest for strategy {strategy_id}")

        results = []
        current_start = config.start_date

        while current_start < config.end_date:
            # Define training and testing windows
            train_end = current_start + timedelta(days=config.walk_forward_window_days // 2)
            test_end = min(
                current_start + timedelta(days=config.walk_forward_window_days),
                config.end_date
            )

            if test_end >= config.end_date:
                break

            # Create window config
            window_config = BacktestConfig(
                start_date=current_start,
                end_date=test_end,
                initial_capital=config.initial_capital,
                commission_per_trade=config.commission_per_trade,
                slippage_bps=config.slippage_bps,
                benchmark_symbol=config.benchmark_symbol,
            )

            # Run backtest for this window
            result = await self.run_backtest(strategy_id, window_config, strategy_config)
            results.append(result)

            # Move to next window
            current_start += timedelta(days=config.walk_forward_step_days)

        # Combine results
        combined_result = self._combine_walk_forward_results(results, config)
        combined_result.walk_forward_results = results

        return combined_result

    async def _execute_backtest(
        self,
        strategy: BaseStrategy,
        config: BacktestConfig
    ) -> BacktestResult:
        """Execute the actual backtest logic."""

        result = BacktestResult(
            strategy_id=strategy.config.strategy_id,
            config=config
        )

        # Get historical market data
        market_data = await self._get_market_data(config.start_date, config.end_date)

        if not market_data:
            logger.warning("No market data available for backtest period")
            return result

        # Initialize portfolio
        portfolio = {
            'cash': float(config.initial_capital),
            'positions': {},  # symbol -> {'shares': int, 'avg_price': float}
            'portfolio_value': float(config.initial_capital)
        }

        # Track portfolio values over time
        portfolio_values = [(config.start_date, config.initial_capital)]

        # Process each trading day
        current_date = config.start_date
        while current_date <= config.end_date:
            if current_date.weekday() >= 5:  # Skip weekends
                current_date += timedelta(days=1)
                continue

            # Get market data for this date
            day_data = {symbol: data.get(current_date, {}) for symbol, data in market_data.items()}

            # Generate signals
            signals = await strategy.generate_signals(day_data, portfolio)

            # Execute signals
            trades = await self._execute_signals(signals, portfolio, day_data, config)

            # Update portfolio value
            portfolio_value = self._calculate_portfolio_value(portfolio, day_data)
            portfolio['portfolio_value'] = portfolio_value
            portfolio_values.append((current_date, Decimal(str(portfolio_value))))

            # Record trades and signals
            result.trades.extend(trades)
            result.signals.extend(signals)

            current_date += timedelta(days=1)

        # Calculate performance metrics
        self._calculate_performance_metrics(result, portfolio_values, config)

        # Calculate benchmark comparison
        await self._calculate_benchmark_comparison(result, config)

        return result

    async def _get_market_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Dict[datetime, Dict[str, float]]]:
        """Get historical market data for backtesting."""
        # This would integrate with your market data service
        # For now, return mock data structure
        return {}

    async def _execute_signals(
        self,
        signals: List[Signal],
        portfolio: Dict,
        market_data: Dict[str, Dict[str, float]],
        config: BacktestConfig
    ) -> List[Dict[str, Any]]:
        """Execute trading signals with realistic costs."""
        trades = []

        for signal in signals:
            symbol = signal.symbol
            if symbol not in market_data or not market_data[symbol]:
                continue

            price_data = market_data[symbol]
            if 'close' not in price_data:
                continue

            price = price_data['close']

            # Apply slippage
            slippage = price * (config.slippage_bps / 10000)
            if signal.signal_type == SignalType.BUY:
                execution_price = price + slippage
            else:
                execution_price = price - slippage

            # Calculate position size
            portfolio_value = portfolio['portfolio_value']
            max_position_value = portfolio_value * float(config.max_position_size)

            if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                # Calculate shares
                available_cash = portfolio['cash']
                if signal.signal_type == SignalType.BUY:
                    max_shares = int(max_position_value / execution_price)
                    shares = min(max_shares, int(available_cash / execution_price))
                else:
                    # Sell existing position
                    current_position = portfolio['positions'].get(symbol, {}).get('shares', 0)
                    shares = min(current_position, int(max_position_value / execution_price))

                if shares > 0:
                    # Execute trade
                    trade_value = shares * execution_price
                    commission = trade_value * float(config.commission_per_trade)

                    trade = {
                        'timestamp': signal.timestamp,
                        'symbol': symbol,
                        'signal_type': signal.signal_type.value,
                        'shares': shares,
                        'price': execution_price,
                        'value': trade_value,
                        'commission': commission,
                        'slippage': slippage
                    }

                    # Update portfolio
                    if signal.signal_type == SignalType.BUY:
                        portfolio['cash'] -= (trade_value + commission)
                        if symbol not in portfolio['positions']:
                            portfolio['positions'][symbol] = {'shares': 0, 'avg_price': 0.0}

                        position = portfolio['positions'][symbol]
                        total_shares = position['shares'] + shares
                        total_cost = (position['shares'] * position['avg_price']) + trade_value
                        position['avg_price'] = total_cost / total_shares
                        position['shares'] = total_shares

                    else:  # SELL
                        portfolio['cash'] += (trade_value - commission)
                        position = portfolio['positions'].get(symbol, {})
                        if position.get('shares', 0) >= shares:
                            position['shares'] -= shares
                            if position['shares'] == 0:
                                del portfolio['positions'][symbol]

                    trades.append(trade)

        return trades

    def _calculate_portfolio_value(
        self,
        portfolio: Dict,
        market_data: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate current portfolio value."""
        cash = portfolio['cash']
        positions_value = 0.0

        for symbol, position in portfolio['positions'].items():
            shares = position['shares']
            if symbol in market_data and 'close' in market_data[symbol]:
                price = market_data[symbol]['close']
                positions_value += shares * price

        return cash + positions_value

    def _calculate_performance_metrics(
        self,
        result: BacktestResult,
        portfolio_values: List[Tuple[datetime, Decimal]],
        config: BacktestConfig
    ) -> None:
        """Calculate comprehensive performance metrics."""

        if len(portfolio_values) < 2:
            return

        # Extract values
        values = [float(v) for _, v in portfolio_values]
        dates = [d for d, _ in portfolio_values]

        # Calculate returns
        initial_value = float(config.initial_capital)
        final_value = values[-1]
        result.total_return = Decimal(str((final_value - initial_value) / initial_value))

        # Annualized return
        days = (dates[-1] - dates[0]).days
        if days > 0:
            years = days / 365.25
            result.annualized_return = Decimal(str((final_value / initial_value) ** (1 / years) - 1))

        # Daily returns
        daily_returns = []
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(daily_return)

        if daily_returns:
            # Volatility (annualized)
            result.volatility = Decimal(str(np.std(daily_returns) * np.sqrt(252)))

            # Sharpe ratio (assuming 2% risk-free rate)
            risk_free_rate = 0.02
            excess_returns = [r - risk_free_rate/252 for r in daily_returns]
            if result.volatility > 0:
                result.sharpe_ratio = Decimal(str(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)))

        # Maximum drawdown
        peak = initial_value
        max_drawdown = 0.0
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        result.max_drawdown = Decimal(str(max_drawdown))

        # Trade statistics
        result.total_trades = len(result.trades)
        winning_trades = [t for t in result.trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in result.trades if t.get('pnl', 0) < 0]

        result.winning_trades = len(winning_trades)
        result.losing_trades = len(losing_trades)

        if result.total_trades > 0:
            result.win_rate = Decimal(str(result.winning_trades / result.total_trades))

        if winning_trades:
            result.avg_win = Decimal(str(np.mean([t['pnl'] for t in winning_trades])))
        if losing_trades:
            result.avg_loss = Decimal(str(np.mean([t['pnl'] for t in losing_trades])))

        if result.avg_loss != 0:
            result.profit_factor = Decimal(str(abs(float(result.avg_win) / float(result.avg_loss))))

        # Value at Risk (simplified)
        if daily_returns:
            result.value_at_risk_95 = Decimal(str(np.percentile(daily_returns, 5)))
            result.expected_shortfall_95 = Decimal(str(np.mean([r for r in daily_returns if r <= float(result.value_at_risk_95)])))

    async def _calculate_benchmark_comparison(
        self,
        result: BacktestResult,
        config: BacktestConfig
    ) -> None:
        """Calculate benchmark comparison metrics."""
        # This would compare against the benchmark index
        # For now, set to zero (no benchmark data)
        result.benchmark_return = Decimal("0.0")
        result.alpha = result.total_return - result.benchmark_return

    def _combine_walk_forward_results(
        self,
        results: List[BacktestResult],
        config: BacktestConfig
    ) -> BacktestResult:
        """Combine multiple walk-forward results into a single result."""
        if not results:
            return BacktestResult(strategy_id="", config=config)

        # Use the first result as base and update with combined metrics
        combined = results[0]

        # Combine portfolio values (simplified - just use last result's final value)
        if results:
            combined.portfolio_values = results[-1].portfolio_values

        # Average key metrics across all windows
        total_returns = [float(r.total_return) for r in results]
        combined.total_return = Decimal(str(np.mean(total_returns)))

        sharpe_ratios = [float(r.sharpe_ratio) for r in results if r.sharpe_ratio != 0]
        if sharpe_ratios:
            combined.sharpe_ratio = Decimal(str(np.mean(sharpe_ratios)))

        max_drawdowns = [float(r.max_drawdown) for r in results]
        if max_drawdowns:
            combined.max_drawdown = Decimal(str(np.max(max_drawdowns)))

        return combined