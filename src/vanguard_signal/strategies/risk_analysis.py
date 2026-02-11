"""
risk_analysis.py — Comprehensive risk analysis and stress testing framework.

Provides advanced risk analytics including:
- Value at Risk (VaR) calculations (Historical, Parametric, Monte Carlo)
- Conditional Value at Risk (CVaR/Expected Shortfall)
- Risk factor decomposition and attribution
- Stress testing with predefined and custom scenarios
- Monte Carlo simulation for risk assessment
- Risk-adjusted performance metrics
- Scenario analysis and sensitivity testing
- Risk reporting and visualization support
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Union
from uuid import uuid4

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from sklearn.decomposition import PCA

from .backtesting import BacktestingEngine, BacktestConfig, BacktestResult
from .performance import PerformanceAnalyzer, PerformanceMetrics
from .base import StrategyConfig
from .registry import StrategyRegistry

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for strategy analysis."""

    # Value at Risk metrics
    var_95: float = 0.0  # 95% VaR
    var_99: float = 0.0  # 99% VaR
    cvar_95: float = 0.0  # 95% CVaR (Expected Shortfall)
    cvar_99: float = 0.0  # 99% CVaR

    # Volatility metrics
    volatility: float = 0.0  # Annualized volatility
    downside_volatility: float = 0.0  # Downside deviation
    maximum_drawdown: float = 0.0  # Maximum drawdown
    average_drawdown: float = 0.0  # Average drawdown

    # Tail risk metrics
    skewness: float = 0.0  # Return distribution skewness
    kurtosis: float = 0.0  # Return distribution kurtosis
    tail_ratio: float = 0.0  # Tail ratio (95th/5th percentile)

    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0  # Downside Sharpe ratio
    calmar_ratio: float = 0.0  # Return/Max Drawdown ratio
    omega_ratio: float = 0.0  # Omega ratio (gains/losses above threshold)

    # Liquidity and concentration
    concentration_ratio: float = 0.0  # Portfolio concentration
    liquidity_ratio: float = 0.0  # Liquidity risk measure

    # Stress test results
    stress_test_losses: Dict[str, float] = field(default_factory=dict)
    scenario_impacts: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Risk attribution
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    risk_contributions: Dict[str, float] = field(default_factory=dict)


@dataclass
class StressTestScenario:
    """Definition of a stress test scenario."""

    scenario_id: str
    name: str
    description: str

    # Market shock parameters
    equity_shock: float = 0.0  # Equity market shock (-0.2 = -20%)
    volatility_shock: float = 0.0  # Volatility increase (0.5 = 50% increase)
    interest_rate_shock: float = 0.0  # Interest rate change in basis points
    credit_spread_shock: float = 0.0  # Credit spread widening in basis points

    # Asset-specific shocks
    asset_shocks: Dict[str, float] = field(default_factory=dict)  # Asset-specific shocks

    # Correlation changes
    correlation_shock: float = 0.0  # Change in correlations (0.2 = 20% increase)

    # Liquidity shock
    liquidity_shock: float = 0.0  # Liquidity premium increase

    # Time horizon
    horizon_days: int = 1  # Stress period in days

    # Probability weight (for scenario analysis)
    probability_weight: float = 1.0


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo risk simulation."""

    n_simulations: int = 10000
    time_horizon_days: int = 252  # 1 year
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99, 0.999])

    # Simulation parameters
    use_empirical_distribution: bool = True  # Use historical returns vs parametric
    include_volatility_clustering: bool = True  # GARCH effects
    include_jump_risk: bool = False  # Jump diffusion model

    # Risk factors to simulate
    simulate_equity_risk: bool = True
    simulate_interest_rate_risk: bool = True
    simulate_credit_risk: bool = True
    simulate_liquidity_risk: bool = False

    # Correlation structure
    use_dynamic_correlations: bool = False  # DCC-GARCH correlations


@dataclass
class StressTestResult:
    """Results from stress testing analysis."""

    scenario_id: str
    scenario_name: str
    portfolio_loss: float
    portfolio_loss_pct: float
    var_breached: bool  # Whether scenario exceeds VaR
    cvar_breached: bool  # Whether scenario exceeds CVaR

    # Component breakdowns
    equity_contribution: float = 0.0
    volatility_contribution: float = 0.0
    interest_rate_contribution: float = 0.0
    credit_contribution: float = 0.0
    liquidity_contribution: float = 0.0

    # Risk metrics under stress
    stressed_volatility: float = 0.0
    stressed_var_99: float = 0.0
    stressed_sharpe: float = 0.0

    # Recovery analysis
    recovery_time_days: Optional[int] = None
    recovery_loss_pct: float = 0.0


@dataclass
class RiskAnalysisResult:
    """Complete risk analysis results."""

    strategy_id: str
    base_metrics: RiskMetrics
    analysis_id: str = field(default_factory=lambda: str(uuid4()))
    analysis_date: datetime = field(default_factory=datetime.now)

    # Stress test results
    stress_test_results: List[StressTestResult] = field(default_factory=list)

    # Monte Carlo results
    monte_carlo_var: Dict[float, float] = field(default_factory=dict)
    monte_carlo_cvar: Dict[float, float] = field(default_factory=dict)
    simulation_paths: Optional[np.ndarray] = None

    # Risk factor analysis
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    risk_attribution: Dict[str, float] = field(default_factory=dict)

    # Scenario analysis
    scenario_analysis: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Risk limits and breaches
    risk_limits_breached: List[str] = field(default_factory=list)
    risk_warnings: List[str] = field(default_factory=list)

    # Recommendations
    risk_recommendations: List[str] = field(default_factory=list)


class RiskCalculator:
    """Core risk metrics calculator."""

    def __init__(self, confidence_level: float = 0.95, annualization_factor: int = 252):
        self.confidence_level = confidence_level
        self.annualization_factor = annualization_factor

    def calculate_var_historical(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate Historical Value at Risk."""
        if len(returns) < 10:
            return 0.0

        # Sort returns in ascending order (worst to best)
        sorted_returns = np.sort(returns)

        # Find the return at the confidence level
        index = int((1 - confidence_level) * len(sorted_returns))
        var = -sorted_returns[index]  # Negative because we want loss magnitude

        return float(var)

    def calculate_var_parametric(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate Parametric Value at Risk (assuming normal distribution)."""
        if len(returns) < 10:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        # For normal distribution, VaR = - (mean + z * std)
        z_score = stats.norm.ppf(1 - confidence_level)
        var = -(mean_return + z_score * std_return)

        return float(var)

    def calculate_var_monte_carlo(self, returns: np.ndarray, n_simulations: int = 10000,
                                 confidence_level: float = 0.95) -> float:
        """Calculate Monte Carlo Value at Risk."""
        if len(returns) < 10:
            return 0.0

        # Bootstrap resampling
        simulated_returns = np.random.choice(returns, size=(n_simulations, len(returns)), replace=True)
        portfolio_returns = np.sum(simulated_returns, axis=1)

        # Calculate VaR from simulated portfolio returns
        sorted_returns = np.sort(portfolio_returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        var = -sorted_returns[index]

        return float(var)

    def calculate_cvar(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        if len(returns) < 10:
            return 0.0

        # Sort returns in ascending order
        sorted_returns = np.sort(returns)

        # Find returns beyond VaR threshold
        var_index = int((1 - confidence_level) * len(sorted_returns))
        tail_returns = sorted_returns[:var_index + 1]

        # CVaR is the average of returns beyond VaR
        cvar = -np.mean(tail_returns)

        return float(cvar)

    def calculate_volatility_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate various volatility metrics."""
        if len(returns) < 10:
            return {
                'volatility': 0.0,
                'downside_volatility': 0.0,
                'maximum_drawdown': 0.0,
                'average_drawdown': 0.0
            }

        # Annualized volatility
        volatility = np.std(returns, ddof=1) * np.sqrt(self.annualization_factor)

        # Downside volatility (only negative returns)
        negative_returns = returns[returns < 0]
        downside_volatility = np.std(negative_returns, ddof=1) * np.sqrt(self.annualization_factor) if len(negative_returns) > 0 else 0.0

        # Maximum drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = -np.min(drawdowns) if len(drawdowns) > 0 else 0.0

        # Average drawdown
        avg_drawdown = -np.mean(drawdowns[drawdowns < 0]) if np.any(drawdowns < 0) else 0.0

        return {
            'volatility': float(volatility),
            'downside_volatility': float(downside_volatility),
            'maximum_drawdown': float(max_drawdown),
            'average_drawdown': float(avg_drawdown)
        }

    def calculate_tail_risk_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate tail risk metrics."""
        if len(returns) < 10:
            return {
                'skewness': 0.0,
                'kurtosis': 0.0,
                'tail_ratio': 0.0
            }

        # Skewness and kurtosis
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns, fisher=True)  # Excess kurtosis

        # Tail ratio (95th percentile / 5th percentile)
        percentile_95 = np.percentile(returns, 95)
        percentile_5 = np.percentile(returns, 5)
        tail_ratio = percentile_95 / abs(percentile_5) if percentile_5 != 0 else 0.0

        return {
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'tail_ratio': float(tail_ratio)
        }

    def calculate_risk_adjusted_returns(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> Dict[str, float]:
        """Calculate risk-adjusted return metrics."""
        if len(returns) < 10:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'omega_ratio': 0.0
            }

        mean_return = np.mean(returns)
        volatility = np.std(returns, ddof=1)

        # Sharpe ratio
        sharpe_ratio = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0.0

        # Sortino ratio (using downside volatility)
        negative_returns = returns[returns < 0]
        downside_volatility = np.std(negative_returns, ddof=1) if len(negative_returns) > 0 else 0.0
        sortino_ratio = (mean_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0.0

        # Calmar ratio (annualized return / max drawdown)
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = -np.min(drawdowns) if len(drawdowns) > 0 else 0.0
        annualized_return = mean_return * self.annualization_factor
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0

        # Omega ratio (probability weighted gains vs losses)
        threshold = risk_free_rate
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns < threshold]

        omega_ratio = np.sum(gains) / np.sum(losses) if np.sum(losses) > 0 else 0.0

        return {
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'omega_ratio': float(omega_ratio)
        }


class StressTester:
    """Stress testing engine for portfolio risk analysis."""

    def __init__(self):
        self.predefined_scenarios = self._create_predefined_scenarios()

    def _create_predefined_scenarios(self) -> Dict[str, StressTestScenario]:
        """Create predefined stress test scenarios."""
        return {
            'black_monday_1987': StressTestScenario(
                scenario_id='black_monday_1987',
                name='Black Monday 1987',
                description='22.6% single-day market crash',
                equity_shock=-0.226,
                volatility_shock=1.5,
                horizon_days=1
            ),
            'dot_com_crash': StressTestScenario(
                scenario_id='dot_com_crash',
                name='Dot-com Crash 2000-2002',
                description='Tech bubble burst with 78% NASDAQ decline',
                equity_shock=-0.5,
                volatility_shock=0.8,
                horizon_days=252 * 2
            ),
            'financial_crisis_2008': StressTestScenario(
                scenario_id='financial_crisis_2008',
                name='Financial Crisis 2008',
                description='Global financial crisis with 57% S&P 500 decline',
                equity_shock=-0.57,
                volatility_shock=1.2,
                interest_rate_shock=-200,  # Fed rate cuts
                credit_spread_shock=300,   # Credit spreads widen
                horizon_days=252
            ),
            'covid_crash_2020': StressTestScenario(
                scenario_id='covid_crash_2020',
                name='COVID-19 Crash 2020',
                description='Fastest bear market in history',
                equity_shock=-0.34,
                volatility_shock=2.0,
                interest_rate_shock=-150,
                horizon_days=30
            ),
            'volatility_spike': StressTestScenario(
                scenario_id='volatility_spike',
                name='Volatility Spike',
                description='Sudden increase in market volatility',
                volatility_shock=3.0,
                correlation_shock=0.5,
                horizon_days=5
            ),
            'rate_hike_cycle': StressTestScenario(
                scenario_id='rate_hike_cycle',
                name='Fed Rate Hike Cycle',
                description='500bps rate increase over 12 months',
                interest_rate_shock=500,
                equity_shock=-0.15,
                horizon_days=252
            ),
            'liquidity_crisis': StressTestScenario(
                scenario_id='liquidity_crisis',
                name='Liquidity Crisis',
                description='Sudden liquidity dry-up',
                liquidity_shock=0.05,  # 5% liquidity premium
                volatility_shock=1.5,
                horizon_days=10
            )
        }

    def get_predefined_scenario(self, scenario_id: str) -> Optional[StressTestScenario]:
        """Get a predefined stress test scenario."""
        return self.predefined_scenarios.get(scenario_id)

    def list_predefined_scenarios(self) -> List[Dict[str, Any]]:
        """List all predefined scenarios."""
        return [
            {
                'id': scenario.scenario_id,
                'name': scenario.name,
                'description': scenario.description,
                'horizon_days': scenario.horizon_days
            }
            for scenario in self.predefined_scenarios.values()
        ]

    def apply_stress_scenario(self, returns: np.ndarray, scenario: StressTestScenario) -> np.ndarray:
        """Apply a stress scenario to return series."""
        stressed_returns = returns.copy()

        # Apply equity shock
        if scenario.equity_shock != 0:
            # Amplify negative returns during stress
            stressed_returns = stressed_returns * (1 + scenario.equity_shock)

        # Apply volatility shock
        if scenario.volatility_shock != 0:
            current_vol = np.std(stressed_returns, ddof=1)
            target_vol = current_vol * (1 + scenario.volatility_shock)
            stressed_returns = stressed_returns * (target_vol / current_vol) if current_vol > 0 else stressed_returns

        # Apply correlation shock (simplified - increases cross-asset correlation)
        if scenario.correlation_shock != 0:
            # This is a simplified implementation
            # In practice, would need correlation matrix adjustments
            stressed_returns = stressed_returns * (1 + scenario.correlation_shock * np.random.normal(0, 0.1, len(stressed_returns)))

        # Apply liquidity shock
        if scenario.liquidity_shock != 0:
            # Add liquidity premium to returns
            liquidity_cost = np.abs(stressed_returns) * scenario.liquidity_shock
            stressed_returns = stressed_returns - liquidity_cost

        return stressed_returns

    def calculate_scenario_impact(self, returns: np.ndarray, scenario: StressTestScenario) -> StressTestResult:
        """Calculate the impact of a stress scenario."""
        stressed_returns = self.apply_stress_scenario(returns, scenario)

        # Calculate portfolio loss
        portfolio_loss = np.sum(stressed_returns)
        portfolio_loss_pct = portfolio_loss / abs(np.sum(returns[returns > 0])) if np.sum(returns[returns > 0]) != 0 else 0.0

        # Calculate risk metrics under stress
        stressed_volatility = np.std(stressed_returns, ddof=1) * np.sqrt(252)  # Annualized

        # Calculate VaR under stress
        risk_calc = RiskCalculator()
        stressed_var_99 = risk_calc.calculate_var_historical(stressed_returns, 0.99)

        # Calculate Sharpe ratio under stress
        mean_return = np.mean(stressed_returns)
        stressed_sharpe = mean_return / stressed_volatility if stressed_volatility > 0 else 0.0

        # Check if scenario breaches VaR/CVaR
        base_var_99 = risk_calc.calculate_var_historical(returns, 0.99)
        base_cvar_99 = risk_calc.calculate_cvar(returns, 0.99)

        var_breached = abs(portfolio_loss) > base_var_99
        cvar_breached = abs(portfolio_loss) > base_cvar_99

        # Recovery analysis (simplified)
        cumulative_stressed = np.cumprod(1 + stressed_returns)
        recovery_time = None
        if np.min(cumulative_stressed) < 0.8:  # 20% loss threshold
            recovery_idx = np.where(cumulative_stressed >= 0.95)[0]  # 95% recovery
            if len(recovery_idx) > 0:
                recovery_time = int(recovery_idx[0])

        return StressTestResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            portfolio_loss=float(portfolio_loss),
            portfolio_loss_pct=float(portfolio_loss_pct),
            var_breached=var_breached,
            cvar_breached=cvar_breached,
            stressed_volatility=float(stressed_volatility),
            stressed_var_99=float(stressed_var_99),
            stressed_sharpe=float(stressed_sharpe),
            recovery_time_days=recovery_time
        )


class MonteCarloSimulator:
    """Monte Carlo simulation engine for risk analysis."""

    def __init__(self, config: MonteCarloConfig):
        self.config = config

    def simulate_returns(self, historical_returns: np.ndarray) -> np.ndarray:
        """Run Monte Carlo simulations of portfolio returns."""
        n_simulations = self.config.n_simulations
        horizon = self.config.time_horizon_days

        # Initialize simulation matrix
        simulations = np.zeros((n_simulations, horizon))

        if self.config.use_empirical_distribution:
            # Use empirical distribution (bootstrap)
            for i in range(n_simulations):
                # Bootstrap resample from historical returns
                simulated_path = np.random.choice(historical_returns, size=horizon, replace=True)
                simulations[i, :] = simulated_path
        else:
            # Use parametric distribution (normal)
            mean_return = np.mean(historical_returns)
            std_return = np.std(historical_returns, ddof=1)

            for i in range(n_simulations):
                # Generate random normal returns
                simulated_path = np.random.normal(mean_return, std_return, horizon)
                simulations[i, :] = simulated_path

        return simulations

    def calculate_simulated_var(self, simulations: np.ndarray) -> Dict[float, float]:
        """Calculate Value at Risk from Monte Carlo simulations."""
        var_results = {}

        for confidence_level in self.config.confidence_levels:
            # Calculate portfolio returns for each simulation
            portfolio_returns = np.sum(simulations, axis=1)

            # Sort returns and find VaR
            sorted_returns = np.sort(portfolio_returns)
            index = int((1 - confidence_level) * len(sorted_returns))
            var = -sorted_returns[index]

            var_results[confidence_level] = float(var)

        return var_results

    def calculate_simulated_cvar(self, simulations: np.ndarray) -> Dict[float, float]:
        """Calculate Conditional VaR from Monte Carlo simulations."""
        cvar_results = {}

        for confidence_level in self.config.confidence_levels:
            portfolio_returns = np.sum(simulations, axis=1)
            sorted_returns = np.sort(portfolio_returns)

            # Find returns beyond VaR threshold
            var_index = int((1 - confidence_level) * len(sorted_returns))
            tail_returns = sorted_returns[:var_index + 1]

            # CVaR is the average of returns beyond VaR
            cvar = -np.mean(tail_returns)

            cvar_results[confidence_level] = float(cvar)

        return cvar_results


class RiskAnalysisEngine:
    """
    Comprehensive risk analysis engine for trading strategies.

    Features:
    - Complete risk metrics calculation
    - Stress testing with predefined and custom scenarios
    - Monte Carlo risk simulation
    - Risk factor analysis and attribution
    - Scenario analysis and sensitivity testing
    """

    def __init__(self, db_session):
        self.db = db_session
        self.backtesting_engine = BacktestingEngine(db_session)
        self.performance_analyzer = PerformanceAnalyzer()
        self.registry = StrategyRegistry()

        self.risk_calculator = RiskCalculator()
        self.stress_tester = StressTester()

    async def analyze_strategy_risk(
        self,
        strategy_id: str,
        backtest_config: BacktestConfig,
        include_stress_tests: bool = True,
        include_monte_carlo: bool = True,
        monte_carlo_config: Optional[MonteCarloConfig] = None
    ) -> RiskAnalysisResult:
        """
        Perform comprehensive risk analysis for a trading strategy.

        Args:
            strategy_id: ID of the strategy to analyze
            backtest_config: Backtest configuration
            include_stress_tests: Whether to run stress tests
            include_monte_carlo: Whether to run Monte Carlo simulations
            monte_carlo_config: Monte Carlo simulation configuration

        Returns:
            Complete risk analysis results
        """
        logger.info(f"Starting risk analysis for strategy: {strategy_id}")

        result = RiskAnalysisResult(strategy_id=strategy_id)

        # Run backtest to get return series
        backtest_result = await self.backtesting_engine.run_backtest(
            strategy_id, backtest_config, StrategyConfig(strategy_id=strategy_id)
        )

        # Extract returns from backtest result
        returns = np.array([float(trade.pnl) for trade in backtest_result.trades])
        if len(returns) == 0:
            logger.warning("No trades found in backtest result")
            return result

        # Calculate base risk metrics
        result.base_metrics = self._calculate_base_risk_metrics(returns)

        # Run stress tests
        if include_stress_tests:
            result.stress_test_results = await self._run_stress_tests(returns)

        # Run Monte Carlo simulations
        if include_monte_carlo:
            mc_config = monte_carlo_config or MonteCarloConfig()
            mc_results = await self._run_monte_carlo_analysis(returns, mc_config)
            result.monte_carlo_var = mc_results['var']
            result.monte_carlo_cvar = mc_results['cvar']
            result.simulation_paths = mc_results.get('paths')

        # Analyze risk limits and generate recommendations
        self._analyze_risk_limits(result)
        self._generate_risk_recommendations(result)

        logger.info(f"Risk analysis completed for strategy: {strategy_id}")
        return result

    def _calculate_base_risk_metrics(self, returns: np.ndarray) -> RiskMetrics:
        """Calculate comprehensive base risk metrics."""
        metrics = RiskMetrics()

        # VaR calculations
        metrics.var_95 = self.risk_calculator.calculate_var_historical(returns, 0.95)
        metrics.var_99 = self.risk_calculator.calculate_var_historical(returns, 0.99)
        metrics.cvar_95 = self.risk_calculator.calculate_cvar(returns, 0.95)
        metrics.cvar_99 = self.risk_calculator.calculate_cvar(returns, 0.99)

        # Volatility metrics
        vol_metrics = self.risk_calculator.calculate_volatility_metrics(returns)
        metrics.volatility = vol_metrics['volatility']
        metrics.downside_volatility = vol_metrics['downside_volatility']
        metrics.maximum_drawdown = vol_metrics['maximum_drawdown']
        metrics.average_drawdown = vol_metrics['average_drawdown']

        # Tail risk metrics
        tail_metrics = self.risk_calculator.calculate_tail_risk_metrics(returns)
        metrics.skewness = tail_metrics['skewness']
        metrics.kurtosis = tail_metrics['kurtosis']
        metrics.tail_ratio = tail_metrics['tail_ratio']

        # Risk-adjusted returns
        risk_adj_metrics = self.risk_calculator.calculate_risk_adjusted_returns(returns)
        metrics.sharpe_ratio = risk_adj_metrics['sharpe_ratio']
        metrics.sortino_ratio = risk_adj_metrics['sortino_ratio']
        metrics.calmar_ratio = risk_adj_metrics['calmar_ratio']
        metrics.omega_ratio = risk_adj_metrics['omega_ratio']

        return metrics

    async def _run_stress_tests(self, returns: np.ndarray) -> List[StressTestResult]:
        """Run stress tests using predefined scenarios."""
        stress_results = []

        # Run all predefined scenarios
        for scenario in self.stress_tester.predefined_scenarios.values():
            try:
                result = self.stress_tester.calculate_scenario_impact(returns, scenario)
                stress_results.append(result)
            except Exception as e:
                logger.warning(f"Failed to run stress test for scenario {scenario.scenario_id}: {e}")
                continue

        return stress_results

    async def _run_monte_carlo_analysis(self, returns: np.ndarray, config: MonteCarloConfig) -> Dict[str, Any]:
        """Run Monte Carlo risk analysis."""
        simulator = MonteCarloSimulator(config)

        # Run simulations
        simulations = simulator.simulate_returns(returns)

        # Calculate VaR and CVaR from simulations
        var_results = simulator.calculate_simulated_var(simulations)
        cvar_results = simulator.calculate_simulated_cvar(simulations)

        return {
            'var': var_results,
            'cvar': cvar_results,
            'paths': simulations if config.n_simulations <= 1000 else None  # Don't store large arrays
        }

    def _analyze_risk_limits(self, result: RiskAnalysisResult) -> None:
        """Analyze risk limits and identify breaches."""
        metrics = result.base_metrics

        # Define risk limits (these could be configurable)
        risk_limits = {
            'max_drawdown': 0.20,  # 20% max drawdown
            'max_var_99': 0.15,    # 15% max 99% VaR
            'min_sharpe': 0.5,     # Minimum Sharpe ratio
            'max_volatility': 0.30  # 30% max volatility
        }

        # Check for breaches
        if metrics.maximum_drawdown > risk_limits['max_drawdown']:
            result.risk_limits_breached.append(f"Maximum drawdown ({metrics.maximum_drawdown:.1%}) exceeds limit ({risk_limits['max_drawdown']:.1%})")

        if metrics.var_99 > risk_limits['max_var_99']:
            result.risk_limits_breached.append(f"99% VaR ({metrics.var_99:.1%}) exceeds limit ({risk_limits['max_var_99']:.1%})")

        if metrics.sharpe_ratio < risk_limits['min_sharpe']:
            result.risk_limits_breached.append(f"Sharpe ratio ({metrics.sharpe_ratio:.2f}) below minimum ({risk_limits['min_sharpe']:.2f})")

        if metrics.volatility > risk_limits['max_volatility']:
            result.risk_limits_breached.append(f"Volatility ({metrics.volatility:.1%}) exceeds limit ({risk_limits['max_volatility']:.1%})")

        # Check stress test results
        severe_stress_tests = [r for r in result.stress_test_results if r.portfolio_loss_pct > 0.20]  # 20% loss
        if severe_stress_tests:
            result.risk_warnings.append(f"{len(severe_stress_tests)} stress scenarios cause >20% portfolio loss")

    def _generate_risk_recommendations(self, result: RiskAnalysisResult) -> None:
        """Generate risk management recommendations."""
        metrics = result.base_metrics

        # High volatility recommendations
        if metrics.volatility > 0.25:
            result.risk_recommendations.append("Consider position sizing adjustments to reduce portfolio volatility")

        # High drawdown recommendations
        if metrics.maximum_drawdown > 0.15:
            result.risk_recommendations.append("Implement stop-loss mechanisms to limit drawdown exposure")

        # Poor risk-adjusted returns
        if metrics.sharpe_ratio < 0.3:
            result.risk_recommendations.append("Strategy shows poor risk-adjusted returns; consider rebalancing or alternative approaches")

        # Tail risk concerns
        if metrics.kurtosis > 2.0:
            result.risk_recommendations.append("High kurtosis indicates fat tails; consider options strategies for tail risk hedging")

        # Stress test concerns
        severe_impacts = [r for r in result.stress_test_results if r.var_breached or r.cvar_breached]
        if len(severe_impacts) > 3:
            result.risk_recommendations.append("Multiple stress scenarios breach VaR limits; enhance risk controls")

        # Default recommendations
        if not result.risk_recommendations:
            result.risk_recommendations.append("Risk profile appears acceptable; continue monitoring")

    async def create_custom_stress_scenario(
        self,
        name: str,
        description: str,
        equity_shock: float = 0.0,
        volatility_shock: float = 0.0,
        interest_rate_shock: float = 0.0,
        credit_spread_shock: float = 0.0,
        horizon_days: int = 1
    ) -> StressTestScenario:
        """Create a custom stress test scenario."""
        scenario = StressTestScenario(
            scenario_id=f"custom_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}",
            name=name,
            description=description,
            equity_shock=equity_shock,
            volatility_shock=volatility_shock,
            interest_rate_shock=interest_rate_shock,
            credit_spread_shock=credit_spread_shock,
            horizon_days=horizon_days
        )

        return scenario

    def get_risk_report_summary(self, result: RiskAnalysisResult) -> Dict[str, Any]:
        """Generate a summary report of risk analysis results."""
        return {
            'strategy_id': result.strategy_id,
            'analysis_date': result.analysis_date.isoformat(),
            'risk_score': self._calculate_risk_score(result),
            'key_metrics': {
                'sharpe_ratio': result.base_metrics.sharpe_ratio,
                'max_drawdown': result.base_metrics.maximum_drawdown,
                'var_99': result.base_metrics.var_99,
                'volatility': result.base_metrics.volatility
            },
            'stress_test_summary': {
                'scenarios_run': len(result.stress_test_results),
                'severe_impacts': len([r for r in result.stress_test_results if r.portfolio_loss_pct > 0.20]),
                'var_breaches': len([r for r in result.stress_test_results if r.var_breached])
            },
            'risk_warnings': result.risk_warnings,
            'recommendations': result.risk_recommendations
        }

    def _calculate_risk_score(self, result: RiskAnalysisResult) -> float:
        """Calculate an overall risk score (0-100, higher = riskier)."""
        metrics = result.base_metrics

        # Component scores (0-25 each, total 0-100)
        vol_score = min(metrics.volatility * 100, 25)  # Higher volatility = higher score
        dd_score = min(metrics.maximum_drawdown * 100, 25)  # Higher drawdown = higher score
        var_score = min(metrics.var_99 * 100, 25)  # Higher VaR = higher score

        # Sharpe ratio score (inverted - lower Sharpe = higher risk score)
        sharpe_score = max(0, min(25 - metrics.sharpe_ratio * 10, 25))

        # Stress test score
        stress_score = len([r for r in result.stress_test_results if r.var_breached]) * 2
        stress_score = min(stress_score, 25)

        total_score = vol_score + dd_score + var_score + sharpe_score + stress_score

        return min(total_score, 100.0)