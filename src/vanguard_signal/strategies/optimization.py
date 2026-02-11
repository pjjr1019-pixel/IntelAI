"""
optimization.py — Parameter optimization for trading strategies.

Provides comprehensive parameter optimization capabilities including:
- Grid search and random search optimization
- Genetic algorithm optimization
- Cross-validation to prevent overfitting
- Walk-forward optimization for realistic testing
- Multi-objective optimization (return vs risk)
- Parameter sensitivity analysis
- Optimization result visualization and analysis
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Callable
from uuid import uuid4

import numpy as np
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit

from .backtesting import BacktestingEngine, BacktestConfig, BacktestResult
from .performance import PerformanceAnalyzer, PerformanceMetrics
from .base import StrategyConfig
from .registry import StrategyRegistry

logger = logging.getLogger(__name__)


@dataclass
class ParameterRange:
    """Defines a parameter range for optimization."""

    name: str
    min_value: float
    max_value: float
    step: Optional[float] = None  # For grid search
    distribution: str = "uniform"  # uniform, log, normal
    log_base: float = 10.0  # For log distribution

    def sample(self, n_samples: int = 1) -> List[float]:
        """Sample values from this parameter range."""
        if self.distribution == "uniform":
            return np.random.uniform(self.min_value, self.max_value, n_samples).tolist()
        elif self.distribution == "log":
            # Sample in log space then transform back
            log_min = np.log(self.min_value) / np.log(self.log_base)
            log_max = np.log(self.max_value) / np.log(self.log_base)
            log_samples = np.random.uniform(log_min, log_max, n_samples)
            return (self.log_base ** log_samples).tolist()
        elif self.distribution == "normal":
            # Use normal distribution centered between min/max
            mean = (self.min_value + self.max_value) / 2
            std = (self.max_value - self.min_value) / 6  # 99.7% within range
            samples = []
            for _ in range(n_samples):
                sample = np.random.normal(mean, std)
                sample = np.clip(sample, self.min_value, self.max_value)
                samples.append(sample)
            return samples
        else:
            raise ValueError(f"Unknown distribution: {self.distribution}")

    def grid_values(self) -> List[float]:
        """Generate grid values for this parameter."""
        if self.step is None:
            # Default to 10 steps
            n_steps = 10
            return np.linspace(self.min_value, self.max_value, n_steps).tolist()
        else:
            n_steps = int((self.max_value - self.min_value) / self.step) + 1
            return np.linspace(self.min_value, self.max_value, n_steps).tolist()


@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization."""

    # Strategy and parameters
    strategy_id: str
    parameter_ranges: List[ParameterRange]

    # Optimization method
    method: str = "grid"  # grid, random, genetic
    max_evaluations: int = 100

    # Cross-validation
    n_splits: int = 5
    test_size_days: int = 252  # 1 year

    # Objective function
    objective: str = "sharpe_ratio"  # sharpe_ratio, total_return, win_rate, etc.
    maximize: bool = True  # Whether to maximize or minimize objective

    # Constraints
    min_total_return: Optional[float] = None
    max_drawdown_limit: Optional[float] = None

    # Walk-forward optimization
    walk_forward: bool = True
    walk_forward_window_days: int = 252 * 2  # 2 years
    walk_forward_step_days: int = 21  # 1 month

    # Random seed for reproducibility
    random_seed: Optional[int] = None


@dataclass
class OptimizationResult:
    """Results from parameter optimization."""

    config: OptimizationConfig
    optimization_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Best parameters found
    best_parameters: Dict[str, float] = field(default_factory=dict)
    best_score: float = 0.0
    best_metrics: Optional[PerformanceMetrics] = None

    # All evaluation results
    evaluations: List[Dict[str, Any]] = field(default_factory=list)

    # Optimization statistics
    total_evaluations: int = 0
    convergence_score: float = 0.0

    # Cross-validation results
    cv_scores: List[float] = field(default_factory=list)
    cv_mean: float = 0.0
    cv_std: float = 0.0

    # Parameter sensitivity
    parameter_importance: Dict[str, float] = field(default_factory=dict)


class OptimizationAlgorithm(ABC):
    """Abstract base class for optimization algorithms."""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        if config.random_seed:
            np.random.seed(config.random_seed)

    @abstractmethod
    async def optimize(
        self,
        objective_function: Callable[[Dict[str, float]], Awaitable[float]],
        bounds: List[Tuple[float, float]]
    ) -> OptimizationResult:
        """Run the optimization algorithm."""
        pass

    def _create_parameter_dict(self, values: List[float]) -> Dict[str, float]:
        """Convert parameter values list to dictionary."""
        return {param.name: value for param, value in zip(self.config.parameter_ranges, values)}

    def _get_bounds(self) -> List[Tuple[float, float]]:
        """Get parameter bounds for optimization."""
        return [(p.min_value, p.max_value) for p in self.config.parameter_ranges]


class GridSearchOptimizer(OptimizationAlgorithm):
    """Grid search parameter optimization."""

    async def optimize(
        self,
        objective_function: Callable[[Dict[str, float]], Awaitable[float]],
        bounds: List[Tuple[float, float]]
    ) -> OptimizationResult:
        result = OptimizationResult(config=self.config)

        # Generate all parameter combinations
        param_grids = [param.grid_values() for param in self.config.parameter_ranges]
        param_combinations = np.array(np.meshgrid(*param_grids)).T.reshape(-1, len(param_grids))

        logger.info(f"Grid search: evaluating {len(param_combinations)} combinations")

        best_score = float('-inf') if self.config.maximize else float('inf')

        for i, param_values in enumerate(param_combinations):
            if i >= self.config.max_evaluations:
                break

            param_dict = self._create_parameter_dict(param_values.tolist())

            try:
                score = await objective_function(param_dict)
                result.evaluations.append({
                    'parameters': param_dict,
                    'score': score,
                    'evaluation_id': i
                })

                if (self.config.maximize and score > best_score) or \
                   (not self.config.maximize and score < best_score):
                    best_score = score
                    result.best_parameters = param_dict
                    result.best_score = score

            except Exception as e:
                logger.warning(f"Evaluation failed for parameters {param_dict}: {e}")
                continue

        result.total_evaluations = len(result.evaluations)
        result.end_time = datetime.now()

        return result


class RandomSearchOptimizer(OptimizationAlgorithm):
    """Random search parameter optimization."""

    async def optimize(
        self,
        objective_function: Callable[[Dict[str, float]], Awaitable[float]],
        bounds: List[Tuple[float, float]]
    ) -> OptimizationResult:
        result = OptimizationResult(config=self.config)

        logger.info(f"Random search: evaluating {self.config.max_evaluations} random combinations")

        best_score = float('-inf') if self.config.maximize else float('inf')

        for i in range(self.config.max_evaluations):
            # Sample random parameters
            param_values = []
            for param_range in self.config.parameter_ranges:
                samples = param_range.sample(1)
                param_values.append(samples[0])

            param_dict = self._create_parameter_dict(param_values)

            try:
                score = await objective_function(param_dict)
                result.evaluations.append({
                    'parameters': param_dict,
                    'score': score,
                    'evaluation_id': i
                })

                if (self.config.maximize and score > best_score) or \
                   (not self.config.maximize and score < best_score):
                    best_score = score
                    result.best_parameters = param_dict
                    result.best_score = score

            except Exception as e:
                logger.warning(f"Evaluation failed for parameters {param_dict}: {e}")
                continue

        result.total_evaluations = len(result.evaluations)
        result.end_time = datetime.now()

        return result


class GeneticAlgorithmOptimizer(OptimizationAlgorithm):
    """Genetic algorithm parameter optimization."""

    def __init__(self, config: OptimizationConfig, population_size: int = 50, generations: int = 20):
        super().__init__(config)
        self.population_size = population_size
        self.generations = generations

    async def optimize(
        self,
        objective_function: Callable[[Dict[str, float]], Awaitable[float]],
        bounds: List[Tuple[float, float]]
    ) -> OptimizationResult:
        result = OptimizationResult(config=self.config)

        # Initialize population
        population = self._initialize_population()
        fitness_scores = []

        logger.info(f"Genetic algorithm: {self.generations} generations, population size {self.population_size}")

        for generation in range(self.generations):
            # Evaluate fitness
            gen_fitness = []
            for individual in population:
                param_dict = self._create_parameter_dict(individual)
                try:
                    score = await objective_function(param_dict)
                    gen_fitness.append(score)
                    result.evaluations.append({
                        'parameters': param_dict,
                        'score': score,
                        'generation': generation,
                        'evaluation_id': len(result.evaluations)
                    })
                except Exception as e:
                    logger.warning(f"Evaluation failed for parameters {param_dict}: {e}")
                    gen_fitness.append(float('-inf') if self.config.maximize else float('inf'))

            fitness_scores.append(gen_fitness)

            # Find best individual
            best_idx = np.argmax(gen_fitness) if self.config.maximize else np.argmin(gen_fitness)
            best_score = gen_fitness[best_idx]
            best_params = self._create_parameter_dict(population[best_idx])

            if (self.config.maximize and best_score > result.best_score) or \
               (not self.config.maximize and best_score < result.best_score):
                result.best_score = best_score
                result.best_parameters = best_params

            # Create next generation
            if generation < self.generations - 1:
                population = self._evolve_population(population, gen_fitness)

        result.total_evaluations = len(result.evaluations)
        result.end_time = datetime.now()

        return result

    def _initialize_population(self) -> List[List[float]]:
        """Initialize random population."""
        population = []
        for _ in range(self.population_size):
            individual = []
            for param_range in self.config.parameter_ranges:
                samples = param_range.sample(1)
                individual.append(samples[0])
            population.append(individual)
        return population

    def _evolve_population(self, population: List[List[float]], fitness: List[float]) -> List[List[float]]:
        """Evolve population using selection, crossover, and mutation."""
        new_population = []

        # Elitism: keep best individual
        best_idx = np.argmax(fitness) if self.config.maximize else np.argmin(fitness)
        new_population.append(population[best_idx])

        while len(new_population) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_selection(population, fitness)
            parent2 = self._tournament_selection(population, fitness)

            # Crossover
            child = self._crossover(parent1, parent2)

            # Mutation
            child = self._mutate(child)

            new_population.append(child)

        return new_population

    def _tournament_selection(self, population: List[List[float]], fitness: List[float]) -> List[float]:
        """Tournament selection."""
        tournament_size = 3
        candidates = np.random.choice(len(population), tournament_size, replace=False)
        candidate_fitness = [fitness[i] for i in candidates]

        if self.config.maximize:
            winner_idx = candidates[np.argmax(candidate_fitness)]
        else:
            winner_idx = candidates[np.argmin(candidate_fitness)]

        return population[winner_idx]

    def _crossover(self, parent1: List[float], parent2: List[float]) -> List[float]:
        """Single point crossover."""
        if len(parent1) <= 1:
            return parent1.copy()

        crossover_point = np.random.randint(1, len(parent1))
        child = parent1[:crossover_point] + parent2[crossover_point:]
        return child

    def _mutate(self, individual: List[float]) -> List[float]:
        """Gaussian mutation."""
        mutated = individual.copy()
        for i in range(len(mutated)):
            if np.random.random() < 0.1:  # 10% mutation rate
                param_range = self.config.parameter_ranges[i]
                mutation = np.random.normal(0, (param_range.max_value - param_range.min_value) * 0.1)
                mutated[i] = np.clip(mutated[i] + mutation, param_range.min_value, param_range.max_value)
        return mutated


class ParameterOptimizer:
    """
    Main parameter optimization engine for trading strategies.

    Supports multiple optimization algorithms and cross-validation
    to find optimal strategy parameters.
    """

    def __init__(self, db_session):
        self.db = db_session
        self.backtesting_engine = BacktestingEngine(db_session)
        self.performance_analyzer = PerformanceAnalyzer()
        self.registry = StrategyRegistry()

    async def optimize_parameters(
        self,
        config: OptimizationConfig,
        backtest_config: BacktestConfig
    ) -> OptimizationResult:
        """
        Optimize strategy parameters using the specified configuration.

        Args:
            config: Optimization configuration
            backtest_config: Base backtest configuration

        Returns:
            Optimization results with best parameters
        """
        logger.info(f"Starting parameter optimization for strategy {config.strategy_id}")

        # Create objective function
        async def objective_function(parameters: Dict[str, float]) -> float:
            return await self._evaluate_parameters(
                config.strategy_id, parameters, backtest_config, config
            )

        # Select optimization algorithm
        if config.method == "grid":
            optimizer = GridSearchOptimizer(config)
        elif config.method == "random":
            optimizer = RandomSearchOptimizer(config)
        elif config.method == "genetic":
            optimizer = GeneticAlgorithmOptimizer(config)
        else:
            raise ValueError(f"Unknown optimization method: {config.method}")

        # Run optimization
        result = await optimizer.optimize(objective_function, optimizer._get_bounds())

        # Perform cross-validation on best parameters
        if result.best_parameters:
            await self._cross_validate_best_parameters(result, backtest_config)

        # Calculate parameter importance
        self._calculate_parameter_importance(result)

        logger.info(f"Optimization completed: best score = {result.best_score:.4f}")
        return result

    async def _evaluate_parameters(
        self,
        strategy_id: str,
        parameters: Dict[str, float],
        backtest_config: BacktestConfig,
        opt_config: OptimizationConfig
    ) -> float:
        """Evaluate a parameter set by running backtest."""

        # Create strategy config with these parameters
        strategy_config = StrategyConfig(
            strategy_id=strategy_id,
            name=f"Optimized {strategy_id}",
            symbols=backtest_config.benchmark_symbol or ["SPY"],  # Use benchmark as symbol
            parameters=parameters,
        )

        # Run backtest
        if opt_config.walk_forward:
            result = await self.backtesting_engine.run_walk_forward_backtest(
                strategy_id, backtest_config, strategy_config
            )
        else:
            result = await self.backtesting_engine.run_backtest(
                strategy_id, backtest_config, strategy_config
            )

        # Extract objective value
        score = self._extract_objective_score(result, opt_config.objective)

        # Apply constraints
        if not self._check_constraints(result, opt_config):
            # Return worst possible score if constraints not met
            return float('-inf') if opt_config.maximize else float('inf')

        return score

    def _extract_objective_score(self, result: BacktestResult, objective: str) -> float:
        """Extract the objective score from backtest results."""
        if objective == "sharpe_ratio":
            return float(result.sharpe_ratio)
        elif objective == "total_return":
            return float(result.total_return)
        elif objective == "win_rate":
            return float(result.win_rate)
        elif objective == "profit_factor":
            return float(result.profit_factor)
        elif objective == "max_drawdown":
            return -float(result.max_drawdown)  # Negative because we want to minimize drawdown
        elif objective == "recovery_factor":
            return float(result.portfolio_values[-1][1] / result.portfolio_values[0][1]) if result.portfolio_values else 0
        else:
            raise ValueError(f"Unknown objective: {objective}")

    def _check_constraints(self, result: BacktestResult, config: OptimizationConfig) -> bool:
        """Check if result meets optimization constraints."""
        if config.min_total_return is not None:
            if float(result.total_return) < config.min_total_return:
                return False

        if config.max_drawdown_limit is not None:
            if float(result.max_drawdown) > config.max_drawdown_limit:
                return False

        return True

    async def _cross_validate_best_parameters(
        self,
        result: OptimizationResult,
        backtest_config: BacktestConfig
    ) -> None:
        """Perform cross-validation on the best parameters."""
        if not result.best_parameters:
            return

        # Time series split for cross-validation
        total_days = (backtest_config.end_date - backtest_config.start_date).days
        test_size = min(result.config.test_size_days, total_days // (result.config.n_splits + 1))

        tscv = TimeSeriesSplit(n_splits=result.config.n_splits, test_size=test_size)

        dates = [backtest_config.start_date + timedelta(days=i)
                for i in range(0, total_days, 1)]  # Daily dates

        cv_scores = []

        for train_idx, test_idx in tscv.split(dates):
            train_start = dates[train_idx[0]]
            train_end = dates[train_idx[-1]]
            test_start = dates[test_idx[0]]
            test_end = dates[test_idx[-1]]

            # Create test config
            test_config = BacktestConfig(
                start_date=test_start,
                end_date=test_end,
                initial_capital=backtest_config.initial_capital,
                commission_per_trade=backtest_config.commission_per_trade,
                slippage_bps=backtest_config.slippage_bps,
            )

            # Evaluate on test set
            score = await self._evaluate_parameters(
                result.config.strategy_id,
                result.best_parameters,
                test_config,
                result.config
            )

            cv_scores.append(score)

        result.cv_scores = cv_scores
        result.cv_mean = float(np.mean(cv_scores))
        result.cv_std = float(np.std(cv_scores))

    def _calculate_parameter_importance(self, result: OptimizationResult) -> None:
        """Calculate parameter importance using correlation analysis."""
        if len(result.evaluations) < 10:
            return

        # Extract parameter values and scores
        param_names = list(result.config.parameter_ranges.keys())
        param_values = []
        scores = []

        for eval_result in result.evaluations:
            if 'parameters' in eval_result and 'score' in eval_result:
                param_values.append([eval_result['parameters'][name] for name in param_names])
                scores.append(eval_result['score'])

        if not param_values or not scores:
            return

        # Calculate correlation between each parameter and score
        param_values = np.array(param_values)
        scores = np.array(scores)

        importance = {}
        for i, param_name in enumerate(param_names):
            if np.std(param_values[:, i]) > 0:  # Avoid division by zero
                corr, _ = stats.pearsonr(param_values[:, i], scores)
                importance[param_name] = abs(corr)  # Use absolute correlation
            else:
                importance[param_name] = 0.0

        result.parameter_importance = importance

    async def sensitivity_analysis(
        self,
        strategy_id: str,
        base_parameters: Dict[str, float],
        backtest_config: BacktestConfig,
        sensitivity_range: float = 0.1
    ) -> Dict[str, List[Tuple[float, float]]]:
        """
        Perform sensitivity analysis on parameters.

        Args:
            strategy_id: Strategy to analyze
            base_parameters: Base parameter values
            backtest_config: Backtest configuration
            sensitivity_range: Range for sensitivity analysis (±10% by default)

        Returns:
            Dictionary mapping parameter names to (parameter_value, score) pairs
        """
        sensitivity_results = {}

        for param_name, base_value in base_parameters.items():
            param_sensitivity = []

            # Test parameter values around base value
            test_values = np.linspace(
                base_value * (1 - sensitivity_range),
                base_value * (1 + sensitivity_range),
                11  # 11 test points
            )

            for test_value in test_values:
                test_params = base_parameters.copy()
                test_params[param_name] = test_value

                score = await self._evaluate_parameters(
                    strategy_id, test_params, backtest_config,
                    OptimizationConfig(strategy_id=strategy_id, parameter_ranges=[])
                )

                param_sensitivity.append((test_value, score))

            sensitivity_results[param_name] = param_sensitivity

        return sensitivity_results