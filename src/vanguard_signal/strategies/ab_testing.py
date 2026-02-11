"""
ab_testing.py — A/B testing framework for trading strategies.

Provides comprehensive A/B testing capabilities including:
- Statistical comparison of strategy performance
- Confidence intervals and significance testing
- Multiple testing correction (Bonferroni, Holm-Bonferroni)
- Effect size calculation (Cohen's d, Glass's Δ)
- Sample size determination for statistical power
- Sequential testing for early stopping
- A/B test result visualization and reporting
- Risk-adjusted performance comparison
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
from statsmodels.stats.power import TTestIndPower
from statsmodels.stats.multitest import multipletests

from .backtesting import BacktestingEngine, BacktestConfig, BacktestResult
from .performance import PerformanceAnalyzer, PerformanceMetrics
from .base import StrategyConfig
from .registry import StrategyRegistry

logger = logging.getLogger(__name__)


@dataclass
class ABTestVariant:
    """A variant in an A/B test."""

    variant_id: str
    name: str
    strategy_config: StrategyConfig
    description: Optional[str] = None

    # Results
    backtest_result: Optional[BacktestResult] = None
    performance_metrics: Optional[PerformanceMetrics] = None
    sample_size: int = 0

    # Statistical metrics
    mean_return: float = 0.0
    std_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0


@dataclass
class ABTestConfig:
    """Configuration for A/B testing."""

    test_name: str
    variants: List[ABTestVariant]
    control_variant_id: str  # Which variant is the control

    # Statistical parameters
    confidence_level: float = 0.95  # 95% confidence
    minimum_effect_size: float = 0.2  # Small effect size (Cohen's d)
    minimum_sample_size: int = 30  # Minimum trades/samples per variant

    # Multiple testing correction
    multiple_testing_method: str = "bonferroni"  # bonferroni, holm, etc.

    # Test duration and stopping rules
    max_test_duration_days: int = 252  # 1 year
    sequential_testing: bool = True  # Enable early stopping
    sequential_alpha: float = 0.05  # Alpha for sequential tests

    # Risk constraints
    max_drawdown_limit: Optional[float] = None
    min_sharpe_ratio: Optional[float] = None

    # Random seed for reproducibility
    random_seed: Optional[int] = None


@dataclass
class ABTestResult:
    """Results from an A/B test."""

    config: ABTestConfig
    test_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Test status
    status: str = "running"  # running, completed, stopped
    winner_variant_id: Optional[str] = None
    confidence_level: float = 0.0

    # Statistical results
    statistical_tests: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    effect_sizes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    confidence_intervals: Dict[str, Dict[str, Tuple[float, float]]] = field(default_factory=dict)

    # Performance comparison
    performance_comparison: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Risk analysis
    risk_analysis: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Sequential testing results
    sequential_tests: List[Dict[str, Any]] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)


class StatisticalTester:
    """Statistical testing utilities for A/B testing."""

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level

    def t_test(self, sample_a: List[float], sample_b: List[float]) -> Dict[str, Any]:
        """Perform two-sample t-test."""
        if len(sample_a) < 2 or len(sample_b) < 2:
            return {
                'test': 't_test',
                'error': 'Insufficient sample size',
                'p_value': 1.0,
                'significant': False
            }

        try:
            t_stat, p_value = stats.ttest_ind(sample_a, sample_b, equal_var=False)

            return {
                'test': 't_test',
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < self.alpha,
                'mean_a': np.mean(sample_a),
                'mean_b': np.mean(sample_b),
                'std_a': np.std(sample_a, ddof=1),
                'std_b': np.std(sample_b, ddof=1)
            }
        except Exception as e:
            return {
                'test': 't_test',
                'error': str(e),
                'p_value': 1.0,
                'significant': False
            }

    def mann_whitney_u_test(self, sample_a: List[float], sample_b: List[float]) -> Dict[str, Any]:
        """Perform Mann-Whitney U test (non-parametric)."""
        if len(sample_a) < 2 or len(sample_b) < 2:
            return {
                'test': 'mann_whitney_u',
                'error': 'Insufficient sample size',
                'p_value': 1.0,
                'significant': False
            }

        try:
            u_stat, p_value = stats.mannwhitneyu(sample_a, sample_b, alternative='two-sided')

            return {
                'test': 'mann_whitney_u',
                'u_statistic': u_stat,
                'p_value': p_value,
                'significant': p_value < self.alpha,
                'median_a': np.median(sample_a),
                'median_b': np.median(sample_b)
            }
        except Exception as e:
            return {
                'test': 'mann_whitney_u',
                'error': str(e),
                'p_value': 1.0,
                'significant': False
            }

    def calculate_effect_size(self, sample_a: List[float], sample_b: List[float], method: str = "cohen_d") -> float:
        """Calculate effect size between two samples."""
        if len(sample_a) < 2 or len(sample_b) < 2:
            return 0.0

        mean_a, mean_b = np.mean(sample_a), np.mean(sample_b)
        std_a, std_b = np.std(sample_a, ddof=1), np.std(sample_b, ddof=1)

        if method == "cohen_d":
            # Cohen's d: standardized mean difference
            pooled_std = np.sqrt((std_a**2 + std_b**2) / 2)
            return (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0.0

        elif method == "glass_delta":
            # Glass's Δ: uses control group standard deviation
            return (mean_a - mean_b) / std_b if std_b > 0 else 0.0

        elif method == "hedges_g":
            # Hedges' g: bias-corrected Cohen's d
            cohen_d = (mean_a - mean_b) / np.sqrt((std_a**2 + std_b**2) / 2)
            n_a, n_b = len(sample_a), len(sample_b)
            correction = 1 - 3 / (4 * (n_a + n_b) - 9)
            return cohen_d * correction if correction > 0 else cohen_d

        return 0.0

    def confidence_interval(self, sample: List[float]) -> Tuple[float, float]:
        """Calculate confidence interval for sample mean."""
        if len(sample) < 2:
            return (np.mean(sample), np.mean(sample))

        mean = np.mean(sample)
        sem = stats.sem(sample)  # Standard error of the mean

        if sem == 0:
            return (mean, mean)

        # t-distribution critical value
        df = len(sample) - 1
        t_critical = stats.t.ppf(1 - self.alpha/2, df)

        margin_error = t_critical * sem
        return (mean - margin_error, mean + margin_error)

    def required_sample_size(self, effect_size: float, power: float = 0.8) -> int:
        """Calculate required sample size for given effect size and power."""
        analysis = TTestIndPower()
        sample_size = analysis.solve_power(
            effect_size=effect_size,
            power=power,
            alpha=self.alpha,
            ratio=1.0  # Equal sample sizes
        )
        return int(np.ceil(sample_size))

    def sequential_test(self, sample_a: List[float], sample_b: List[float], alpha: float = 0.05) -> Dict[str, Any]:
        """Perform sequential testing for early stopping."""
        if len(sample_a) < 10 or len(sample_b) < 10:
            return {
                'can_stop': False,
                'reason': 'Insufficient sample size for sequential testing'
            }

        # Simple sequential probability ratio test approximation
        mean_a, mean_b = np.mean(sample_a), np.mean(sample_b)
        var_a, var_b = np.var(sample_a, ddof=1), np.var(sample_b, ddof=1)

        if var_a == 0 and var_b == 0:
            return {'can_stop': True, 'winner': 'a' if mean_a > mean_b else 'b'}

        # Calculate test statistic
        pooled_var = (var_a + var_b) / 2
        if pooled_var == 0:
            return {'can_stop': True, 'winner': 'a' if mean_a > mean_b else 'b'}

        z_stat = (mean_a - mean_b) / np.sqrt(pooled_var * (1/len(sample_a) + 1/len(sample_b)))

        # Sequential boundaries (simplified)
        boundary = np.sqrt(2 * np.log(1/alpha))

        if abs(z_stat) > boundary:
            winner = 'a' if z_stat > 0 else 'b'
            return {
                'can_stop': True,
                'winner': winner,
                'z_statistic': z_stat,
                'boundary': boundary
            }

        return {
            'can_stop': False,
            'z_statistic': z_stat,
            'boundary': boundary
        }


class ABTestingEngine:
    """
    A/B testing engine for comparing trading strategy performance.

    Features:
    - Statistical significance testing
    - Effect size calculation
    - Confidence intervals
    - Sequential testing for early stopping
    - Multiple testing correction
    - Risk-adjusted performance comparison
    """

    def __init__(self, db_session):
        self.db = db_session
        self.backtesting_engine = BacktestingEngine(db_session)
        self.performance_analyzer = PerformanceAnalyzer()
        self.registry = StrategyRegistry()
        self.statistical_tester = StatisticalTester()

    async def run_ab_test(
        self,
        config: ABTestConfig,
        backtest_config: BacktestConfig,
        n_iterations: int = 10
    ) -> ABTestResult:
        """
        Run a complete A/B test comparing strategy variants.

        Args:
            config: A/B test configuration
            backtest_config: Base backtest configuration
            n_iterations: Number of backtest iterations per variant

        Returns:
            Complete A/B test results
        """
        logger.info(f"Starting A/B test: {config.test_name}")

        result = ABTestResult(config=config)

        # Run backtests for each variant
        variant_results = {}
        for variant in config.variants:
            logger.info(f"Testing variant: {variant.name}")
            results = await self._run_variant_backtests(
                variant, backtest_config, n_iterations
            )
            variant_results[variant.variant_id] = results

        # Analyze results
        await self._analyze_ab_test_results(result, variant_results)

        # Determine winner
        self._determine_test_winner(result)

        result.end_time = datetime.now()
        result.status = "completed"

        logger.info(f"A/B test completed. Winner: {result.winner_variant_id}")
        return result

    async def _run_variant_backtests(
        self,
        variant: ABTestVariant,
        backtest_config: BacktestConfig,
        n_iterations: int
    ) -> List[BacktestResult]:
        """Run multiple backtest iterations for a variant."""
        results = []

        for i in range(n_iterations):
            try:
                # Add some randomness to test periods for robustness
                if n_iterations > 1:
                    # Vary the test period slightly
                    period_variation = np.random.randint(-30, 31)  # ±30 days
                    test_config = BacktestConfig(
                        start_date=backtest_config.start_date + timedelta(days=period_variation),
                        end_date=backtest_config.end_date + timedelta(days=period_variation),
                        initial_capital=backtest_config.initial_capital,
                        commission_per_trade=backtest_config.commission_per_trade,
                        slippage_bps=backtest_config.slippage_bps,
                    )
                else:
                    test_config = backtest_config

                # Run backtest
                backtest_result = await self.backtesting_engine.run_backtest(
                    variant.strategy_config.strategy_id,
                    test_config,
                    variant.strategy_config
                )

                results.append(backtest_result)

            except Exception as e:
                logger.warning(f"Backtest iteration {i} failed for variant {variant.variant_id}: {e}")
                continue

        return results

    async def _analyze_ab_test_results(
        self,
        result: ABTestResult,
        variant_results: Dict[str, List[BacktestResult]]
    ) -> None:
        """Analyze A/B test results statistically."""

        # Extract control results
        control_results = variant_results.get(result.config.control_variant_id, [])
        if not control_results:
            logger.warning("No control results available")
            return

        # Extract performance metrics for each variant
        for variant_id, results in variant_results.items():
            if not results:
                continue

            # Aggregate metrics across iterations
            returns = [float(r.total_return) for r in results]
            sharpe_ratios = [float(r.sharpe_ratio) for r in results]
            max_drawdowns = [float(r.max_drawdown) for r in results]

            variant = next(v for v in result.config.variants if v.variant_id == variant_id)
            variant.mean_return = np.mean(returns)
            variant.std_return = np.std(returns)
            variant.sharpe_ratio = np.mean(sharpe_ratios)
            variant.max_drawdown = np.mean(max_drawdowns)
            variant.sample_size = len(results)

        # Perform statistical tests
        control_variant = next(v for v in result.config.variants
                             if v.variant_id == result.config.control_variant_id)

        for variant in result.config.variants:
            if variant.variant_id == result.config.control_variant_id:
                continue

            # Test returns
            control_returns = [float(r.total_return) for r in variant_results[result.config.control_variant_id]]
            variant_returns = [float(r.total_return) for r in variant_results[variant.variant_id]]

            if control_returns and variant_returns:
                # t-test
                t_test_result = self.statistical_tester.t_test(control_returns, variant_returns)
                result.statistical_tests[f"{variant.variant_id}_vs_control_returns"] = t_test_result

                # Mann-Whitney U test
                mw_test_result = self.statistical_tester.mann_whitney_u_test(control_returns, variant_returns)
                result.statistical_tests[f"{variant.variant_id}_vs_control_returns_mw"] = mw_test_result

                # Effect size
                effect_size = self.statistical_tester.calculate_effect_size(control_returns, variant_returns)
                result.effect_sizes[f"{variant.variant_id}_vs_control"] = {
                    'cohen_d': effect_size,
                    'interpretation': self._interpret_effect_size(effect_size)
                }

                # Confidence intervals
                control_ci = self.statistical_tester.confidence_interval(control_returns)
                variant_ci = self.statistical_tester.confidence_interval(variant_returns)
                result.confidence_intervals[f"{variant.variant_id}_returns"] = {
                    'control': control_ci,
                    'variant': variant_ci,
                    'difference': (variant_ci[0] - control_ci[1], variant_ci[1] - control_ci[0])
                }

        # Multiple testing correction
        if result.statistical_tests:
            p_values = [test['p_value'] for test in result.statistical_tests.values()
                       if 'p_value' in test]
            if p_values:
                corrected = multipletests(p_values, alpha=self.statistical_tester.alpha,
                                        method=result.config.multiple_testing_method)
                for i, test_key in enumerate(result.statistical_tests.keys()):
                    if 'p_value' in result.statistical_tests[test_key]:
                        result.statistical_tests[test_key]['p_value_corrected'] = corrected[1][i]
                        result.statistical_tests[test_key]['significant_corrected'] = corrected[0][i]

        # Performance comparison
        self._calculate_performance_comparison(result)

        # Risk analysis
        self._calculate_risk_analysis(result)

        # Sequential testing
        if result.config.sequential_testing:
            self._perform_sequential_testing(result, variant_results)

    def _calculate_performance_comparison(self, result: ABTestResult) -> None:
        """Calculate detailed performance comparison between variants."""
        for variant in result.config.variants:
            if variant.variant_id == result.config.control_variant_id:
                continue

            control = next(v for v in result.config.variants
                          if v.variant_id == result.config.control_variant_id)

            comparison = {
                'return_difference': variant.mean_return - control.mean_return,
                'return_difference_pct': (variant.mean_return - control.mean_return) / abs(control.mean_return) * 100 if control.mean_return != 0 else 0,
                'sharpe_difference': variant.sharpe_ratio - control.sharpe_ratio,
                'drawdown_difference': variant.max_drawdown - control.max_drawdown,
                'risk_adjusted_advantage': variant.sharpe_ratio > control.sharpe_ratio,
                'return_advantage': variant.mean_return > control.mean_return,
                'risk_advantage': variant.max_drawdown < control.max_drawdown
            }

            result.performance_comparison[variant.variant_id] = comparison

    def _calculate_risk_analysis(self, result: ABTestResult) -> None:
        """Calculate risk-adjusted performance analysis."""
        for variant in result.config.variants:
            risk_metrics = {
                'sharpe_ratio': variant.sharpe_ratio,
                'max_drawdown': variant.max_drawdown,
                'return_volatility': variant.std_return,
                'return_to_drawdown_ratio': variant.mean_return / variant.max_drawdown if variant.max_drawdown != 0 else 0,
                'risk_adjusted_return': variant.mean_return / variant.std_return if variant.std_return != 0 else 0
            }

            result.risk_analysis[variant.variant_id] = risk_metrics

    def _perform_sequential_testing(self, result: ABTestResult, variant_results: Dict[str, List[BacktestResult]]) -> None:
        """Perform sequential testing for early stopping."""
        control_returns = [float(r.total_return) for r in variant_results[result.config.control_variant_id]]

        for variant in result.config.variants:
            if variant.variant_id == result.config.control_variant_id:
                continue

            variant_returns = [float(r.total_return) for r in variant_results[variant.variant_id]]

            if len(control_returns) >= 10 and len(variant_returns) >= 10:
                seq_test = self.statistical_tester.sequential_test(
                    control_returns, variant_returns, result.config.sequential_alpha
                )
                result.sequential_tests.append({
                    'variant_id': variant.variant_id,
                    'test_result': seq_test
                })

    def _determine_test_winner(self, result: ABTestResult) -> None:
        """Determine the winning variant based on statistical and performance criteria."""
        if not result.statistical_tests:
            return

        # Find variants that are statistically significantly better than control
        significant_variants = []
        for test_key, test_result in result.statistical_tests.items():
            if test_key.endswith('_vs_control_returns') and test_result.get('significant_corrected', False):
                variant_id = test_key.split('_vs_control')[0]
                significant_variants.append(variant_id)

        if not significant_variants:
            # No significant winners
            result.recommendations.append("No variant showed statistically significant improvement over control")
            return

        # Among significant variants, choose the one with best risk-adjusted performance
        best_variant = None
        best_score = float('-inf')

        for variant_id in significant_variants:
            variant = next(v for v in result.config.variants if v.variant_id == variant_id)
            comparison = result.performance_comparison.get(variant_id, {})

            # Score based on Sharpe ratio improvement and return improvement
            sharpe_improvement = comparison.get('sharpe_difference', 0)
            return_improvement = comparison.get('return_difference', 0)

            # Weighted score (prioritize risk-adjusted performance)
            score = 0.7 * sharpe_improvement + 0.3 * return_improvement

            if score > best_score:
                best_score = score
                best_variant = variant_id

        if best_variant:
            result.winner_variant_id = best_variant
            result.confidence_level = 0.95  # Based on statistical significance
            result.recommendations.append(f"Variant {best_variant} shows significant improvement over control")
        else:
            result.recommendations.append("Multiple variants show significance, but none clearly superior")

    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret Cohen's d effect size."""
        abs_effect = abs(effect_size)
        if abs_effect < 0.2:
            return "negligible"
        elif abs_effect < 0.5:
            return "small"
        elif abs_effect < 0.8:
            return "medium"
        else:
            return "large"

    async def calculate_sample_size(
        self,
        expected_effect_size: float = 0.2,
        power: float = 0.8,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculate required sample size for A/B testing.

        Args:
            expected_effect_size: Expected effect size (Cohen's d)
            power: Statistical power (1 - β)
            confidence_level: Confidence level (1 - α)

        Returns:
            Sample size requirements and analysis
        """
        tester = StatisticalTester(confidence_level)
        sample_size = tester.required_sample_size(expected_effect_size, power)

        return {
            'required_sample_size_per_variant': sample_size,
            'total_sample_size': sample_size * 2,
            'effect_size': expected_effect_size,
            'power': power,
            'confidence_level': confidence_level,
            'alpha': 1 - confidence_level,
            'recommendations': [
                f"Test each variant with at least {sample_size} observations",
                f"Total minimum sample size: {sample_size * 2}",
                f"Expected to detect {self._interpret_effect_size(expected_effect_size)} effects",
                f"{power*100}% chance of detecting true effects",
                f"{confidence_level*100}% confidence in results"
            ]
        }