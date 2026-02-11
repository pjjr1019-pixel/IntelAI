"""
performance.py — Performance metrics and analysis for trading strategies.

Provides comprehensive performance analysis including:
- Risk-adjusted returns (Sharpe, Sortino ratios)
- Drawdown analysis (maximum, average, recovery time)
- Trade statistics (win rate, profit factor, expectancy)
- Benchmark comparison and alpha calculation
- Risk metrics (VaR, CVaR, maximum loss)
- Performance attribution and decomposition
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a trading strategy."""

    # Return metrics
    total_return: Decimal = Decimal("0.0")
    annualized_return: Decimal = Decimal("0.0")
    compound_annual_growth_rate: Decimal = Decimal("0.0")

    # Risk metrics
    volatility: Decimal = Decimal("0.0")  # Annualized standard deviation
    max_drawdown: Decimal = Decimal("0.0")
    average_drawdown: Decimal = Decimal("0.0")
    longest_drawdown_duration: int = 0  # Days
    average_drawdown_recovery: int = 0  # Days

    # Risk-adjusted returns
    sharpe_ratio: Decimal = Decimal("0.0")
    sortino_ratio: Decimal = Decimal("0.0")  # Downside deviation only
    calmar_ratio: Decimal = Decimal("0.0")  # Return / Max drawdown
    omega_ratio: Decimal = Decimal("0.0")  # Probability weighted ratio

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Decimal("0.0")
    profit_factor: Decimal = Decimal("0.0")
    expectancy: Decimal = Decimal("0.0")  # Expected value per trade
    avg_win: Decimal = Decimal("0.0")
    avg_loss: Decimal = Decimal("0.0")
    largest_win: Decimal = Decimal("0.0")
    largest_loss: Decimal = Decimal("0.0")

    # Risk measures
    value_at_risk_95: Decimal = Decimal("0.0")  # 95% VaR
    value_at_risk_99: Decimal = Decimal("0.0")  # 99% VaR
    conditional_var_95: Decimal = Decimal("0.0")  # 95% CVaR/ES
    conditional_var_99: Decimal = Decimal("0.0")  # 99% CVaR/ES
    maximum_consecutive_losses: int = 0
    maximum_consecutive_wins: int = 0

    # Benchmark comparison
    benchmark_return: Decimal = Decimal("0.0")
    alpha: Decimal = Decimal("0.0")  # Excess return over benchmark
    beta: Decimal = Decimal("0.0")  # Market sensitivity
    tracking_error: Decimal = Decimal("0.0")  # Standard deviation of difference
    information_ratio: Decimal = Decimal("0.0")  # Alpha / Tracking error

    # Additional metrics
    recovery_factor: Decimal = Decimal("0.0")  # Net profit / Max drawdown
    payoff_ratio: Decimal = Decimal("0.0")  # Avg win / Avg loss
    ulcer_index: Decimal = Decimal("0.0")  # Drawdown-based risk measure
    sterling_ratio: Decimal = Decimal("0.0")  # Return / Average drawdown

    # Time-based metrics
    time_in_market: Decimal = Decimal("0.0")  # Percentage of time invested
    avg_trade_duration: int = 0  # Average holding period in days

    # Detailed breakdowns
    monthly_returns: List[Tuple[datetime, Decimal]] = field(default_factory=list)
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)
    trade_analysis: Dict[str, Any] = field(default_factory=dict)


class PerformanceAnalyzer:
    """
    Comprehensive performance analysis for trading strategies.

    Calculates risk-adjusted returns, drawdown analysis, trade statistics,
    and benchmark comparisons.
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize performance analyzer.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe ratio calculation
        """
        self.risk_free_rate = risk_free_rate

    def calculate_metrics(
        self,
        portfolio_values: List[Tuple[datetime, Decimal]],
        trades: List[Dict[str, Any]],
        benchmark_returns: Optional[List[Tuple[datetime, Decimal]]] = None,
        initial_capital: Decimal = Decimal("10000.00")
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            portfolio_values: Time series of portfolio values
            trades: List of executed trades
            benchmark_returns: Time series of benchmark returns
            initial_capital: Starting portfolio value

        Returns:
            Complete performance metrics
        """
        metrics = PerformanceMetrics()

        if not portfolio_values:
            return metrics

        # Extract data
        dates = [d for d, _ in portfolio_values]
        values = [float(v) for _, v in portfolio_values]

        # Basic return metrics
        self._calculate_return_metrics(metrics, values, dates, initial_capital)

        # Risk metrics
        self._calculate_risk_metrics(metrics, values, dates)

        # Risk-adjusted returns
        self._calculate_risk_adjusted_returns(metrics, values, dates)

        # Trade statistics
        self._calculate_trade_statistics(metrics, trades)

        # Benchmark comparison
        if benchmark_returns:
            self._calculate_benchmark_comparison(metrics, portfolio_values, benchmark_returns)

        # Additional analysis
        self._calculate_additional_metrics(metrics, values, dates, trades)

        return metrics

    def _calculate_return_metrics(
        self,
        metrics: PerformanceMetrics,
        values: List[float],
        dates: List[datetime],
        initial_capital: Decimal
    ) -> None:
        """Calculate basic return metrics."""
        initial_value = float(initial_capital)
        final_value = values[-1]

        # Total return
        metrics.total_return = Decimal(str((final_value - initial_value) / initial_value))

        # Annualized return
        days = (dates[-1] - dates[0]).days
        if days > 0:
            years = days / 365.25
            metrics.annualized_return = Decimal(str((final_value / initial_value) ** (1 / years) - 1))

            # CAGR (same as annualized for total period)
            metrics.compound_annual_growth_rate = metrics.annualized_return

    def _calculate_risk_metrics(
        self,
        metrics: PerformanceMetrics,
        values: List[float],
        dates: List[datetime]
    ) -> None:
        """Calculate risk metrics including volatility and drawdowns."""
        # Daily returns
        daily_returns = []
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(daily_return)

        if not daily_returns:
            return

        # Volatility (annualized)
        metrics.volatility = Decimal(str(np.std(daily_returns) * np.sqrt(252)))

        # Drawdown analysis
        self._calculate_drawdown_metrics(metrics, values, dates)

        # Value at Risk
        metrics.value_at_risk_95 = Decimal(str(np.percentile(daily_returns, 5)))
        metrics.value_at_risk_99 = Decimal(str(np.percentile(daily_returns, 1)))

        # Conditional VaR (Expected Shortfall)
        var_95 = float(metrics.value_at_risk_95)
        var_99 = float(metrics.value_at_risk_99)

        tail_returns_95 = [r for r in daily_returns if r <= var_95]
        tail_returns_99 = [r for r in daily_returns if r <= var_99]

        if tail_returns_95:
            metrics.conditional_var_95 = Decimal(str(np.mean(tail_returns_95)))
        if tail_returns_99:
            metrics.conditional_var_99 = Decimal(str(np.mean(tail_returns_99)))

    def _calculate_drawdown_metrics(
        self,
        metrics: PerformanceMetrics,
        values: List[float],
        dates: List[datetime]
    ) -> None:
        """Calculate comprehensive drawdown metrics."""
        peak = values[0]
        max_drawdown = 0.0
        current_drawdown = 0.0
        drawdown_start = None
        drawdowns = []

        for i, value in enumerate(values):
            if value > peak:
                # End current drawdown if exists
                if drawdown_start is not None:
                    drawdown_end = dates[i-1]
                    duration = (drawdown_end - drawdown_start).days
                    recovery = duration if current_drawdown > 0 else 0
                    drawdowns.append({
                        'start': drawdown_start,
                        'end': drawdown_end,
                        'depth': current_drawdown,
                        'duration': duration,
                        'recovery': recovery
                    })
                    drawdown_start = None
                    current_drawdown = 0.0

                peak = value
            else:
                # In drawdown
                current_drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, current_drawdown)

                if drawdown_start is None:
                    drawdown_start = dates[i]

        # Handle final drawdown
        if drawdown_start is not None:
            drawdown_end = dates[-1]
            duration = (drawdown_end - drawdown_start).days
            drawdowns.append({
                'start': drawdown_start,
                'end': drawdown_end,
                'depth': current_drawdown,
                'duration': duration,
                'recovery': 0  # Still in drawdown
            })

        metrics.max_drawdown = Decimal(str(max_drawdown))
        metrics.drawdown_periods = drawdowns

        if drawdowns:
            avg_drawdown = np.mean([d['depth'] for d in drawdowns])
            metrics.average_drawdown = Decimal(str(avg_drawdown))

            durations = [d['duration'] for d in drawdowns]
            metrics.longest_drawdown_duration = max(durations)

            recoveries = [d['recovery'] for d in drawdowns if d['recovery'] > 0]
            if recoveries:
                metrics.average_drawdown_recovery = int(np.mean(recoveries))

    def _calculate_risk_adjusted_returns(
        self,
        metrics: PerformanceMetrics,
        values: List[float],
        dates: List[datetime]
    ) -> None:
        """Calculate risk-adjusted return metrics."""
        # Daily returns
        daily_returns = []
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(daily_return)

        if not daily_returns:
            return

        # Sharpe ratio
        daily_rf = self.risk_free_rate / 252  # Daily risk-free rate
        excess_returns = [r - daily_rf for r in daily_returns]

        if np.std(excess_returns) > 0:
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            metrics.sharpe_ratio = Decimal(str(sharpe))

        # Sortino ratio (downside deviation)
        downside_returns = [r for r in excess_returns if r < 0]
        if downside_returns:
            downside_deviation = np.std(downside_returns)
            if downside_deviation > 0:
                sortino = np.mean(excess_returns) / downside_deviation * np.sqrt(252)
                metrics.sortino_ratio = Decimal(str(sortino))

        # Calmar ratio
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = Decimal(str(float(metrics.annualized_return) / float(metrics.max_drawdown)))

        # Ulcer Index
        if metrics.drawdown_periods:
            ulcer_sum = sum(d['depth'] ** 2 for d in metrics.drawdown_periods)
            ulcer_index = np.sqrt(ulcer_sum / len(metrics.drawdown_periods))
            metrics.ulcer_index = Decimal(str(ulcer_index))

            # Sterling ratio
            if metrics.average_drawdown > 0:
                metrics.sterling_ratio = Decimal(str(float(metrics.annualized_return) / float(metrics.average_drawdown)))

    def _calculate_trade_statistics(
        self,
        metrics: PerformanceMetrics,
        trades: List[Dict[str, Any]]
    ) -> None:
        """Calculate trade-level statistics."""
        if not trades:
            return

        metrics.total_trades = len(trades)

        # Calculate P&L for each trade
        trade_pnls = []
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

        for trade in trades:
            # Calculate P&L (simplified - would need actual entry/exit prices)
            pnl = trade.get('pnl', 0)
            trade_pnls.append(pnl)

            if pnl > 0:
                metrics.winning_trades += 1
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            elif pnl < 0:
                metrics.losing_trades += 1
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        metrics.maximum_consecutive_wins = max_consecutive_wins
        metrics.maximum_consecutive_losses = max_consecutive_losses

        # Win rate
        if metrics.total_trades > 0:
            metrics.win_rate = Decimal(str(metrics.winning_trades / metrics.total_trades))

        # Profit factor
        gross_profit = sum(p for p in trade_pnls if p > 0)
        gross_loss = abs(sum(p for p in trade_pnls if p < 0))

        if gross_loss > 0:
            metrics.profit_factor = Decimal(str(gross_profit / gross_loss))

        # Average win/loss
        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p < 0]

        if wins:
            metrics.avg_win = Decimal(str(np.mean(wins)))
            metrics.largest_win = Decimal(str(max(wins)))

        if losses:
            metrics.avg_loss = Decimal(str(np.mean(losses)))
            metrics.largest_loss = Decimal(str(min(losses)))

        # Payoff ratio
        if metrics.avg_loss != 0:
            metrics.payoff_ratio = Decimal(str(abs(float(metrics.avg_win) / float(metrics.avg_loss))))

        # Expectancy
        if metrics.total_trades > 0:
            win_prob = float(metrics.win_rate)
            avg_win = float(metrics.avg_win)
            avg_loss = float(metrics.avg_loss)
            metrics.expectancy = Decimal(str(win_prob * avg_win + (1 - win_prob) * avg_loss))

    def _calculate_benchmark_comparison(
        self,
        metrics: PerformanceMetrics,
        portfolio_values: List[Tuple[datetime, Decimal]],
        benchmark_returns: List[Tuple[datetime, Decimal]]
    ) -> None:
        """Calculate benchmark comparison metrics."""
        # Align dates and calculate returns
        portfolio_df = pd.DataFrame(portfolio_values, columns=['date', 'value'])
        benchmark_df = pd.DataFrame(benchmark_returns, columns=['date', 'return'])

        # Merge on dates
        merged = pd.merge(portfolio_df, benchmark_df, on='date', how='inner')

        if len(merged) < 2:
            return

        # Calculate portfolio returns
        merged['portfolio_return'] = merged['value'].pct_change()

        # Clean data
        valid_data = merged.dropna()

        if len(valid_data) < 2:
            return

        portfolio_returns = valid_data['portfolio_return'].values
        benchmark_returns_clean = valid_data['return'].values

        # Alpha and Beta (CAPM)
        try:
            covariance = np.cov(portfolio_returns, benchmark_returns_clean)[0, 1]
            benchmark_variance = np.var(benchmark_returns_clean)

            if benchmark_variance > 0:
                metrics.beta = Decimal(str(covariance / benchmark_variance))
                portfolio_mean = np.mean(portfolio_returns)
                benchmark_mean = np.mean(benchmark_returns_clean)
                metrics.alpha = Decimal(str(portfolio_mean - metrics.beta * benchmark_mean))

        except Exception as e:
            logger.warning(f"Error calculating alpha/beta: {e}")

        # Tracking error and Information ratio
        differences = portfolio_returns - benchmark_returns_clean
        metrics.tracking_error = Decimal(str(np.std(differences)))

        if metrics.tracking_error > 0:
            metrics.information_ratio = Decimal(str(float(metrics.alpha) / float(metrics.tracking_error)))

        # Benchmark total return
        if len(benchmark_returns) > 0:
            initial_benchmark = benchmark_returns[0][1]
            final_benchmark = benchmark_returns[-1][1]
            metrics.benchmark_return = Decimal(str((final_benchmark - initial_benchmark) / initial_benchmark))

    def _calculate_additional_metrics(
        self,
        metrics: PerformanceMetrics,
        values: List[float],
        dates: List[datetime],
        trades: List[Dict[str, Any]]
    ) -> None:
        """Calculate additional performance metrics."""
        # Recovery factor
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = Decimal(str(float(metrics.total_return) / float(metrics.max_drawdown)))

        # Monthly returns
        if len(dates) > 30:
            df = pd.DataFrame({'date': dates, 'value': values})
            df['month'] = df['date'].dt.to_period('M')
            monthly = df.groupby('month').agg({
                'value': ['first', 'last']
            }).reset_index()

            for _, row in monthly.iterrows():
                month_start = row['month'].start_time
                monthly_return = (row['value']['last'] - row['value']['first']) / row['value']['first']
                metrics.monthly_returns.append((month_start, Decimal(str(monthly_return))))

        # Trade analysis
        if trades:
            durations = []
            for trade in trades:
                if 'entry_time' in trade and 'exit_time' in trade:
                    duration = (trade['exit_time'] - trade['entry_time']).days
                    durations.append(duration)

            if durations:
                metrics.avg_trade_duration = int(np.mean(durations))

        # Store detailed trade analysis
        metrics.trade_analysis = {
            'total_trades': metrics.total_trades,
            'win_rate': float(metrics.win_rate),
            'profit_factor': float(metrics.profit_factor),
            'expectancy': float(metrics.expectancy),
            'avg_trade_duration': metrics.avg_trade_duration
        }