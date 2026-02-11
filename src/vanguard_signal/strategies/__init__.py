"""
strategies/ — Trading strategy framework and implementations.

This module provides the core strategy framework for implementing,
backtesting, and deploying trading strategies in Intel-AI.

Core Components:
- BaseStrategy: Abstract base class for all trading strategies
- StrategyRegistry: Registry for strategy discovery and management
- StrategyConfig: Configuration management for strategy parameters
- StrategyResult: Standardized results from strategy execution

Strategy Types:
- Signal-based strategies (trend following, mean reversion)
- Portfolio strategies (asset allocation, risk parity)
- Arbitrage strategies (statistical, triangular)
- Machine learning strategies (reinforcement learning, supervised)

Usage:
    from vanguard_signal.strategies import BaseStrategy, StrategyRegistry

    class MyStrategy(BaseStrategy):
        def __init__(self, config):
            super().__init__(config)

        def generate_signals(self, market_data, portfolio):
            # Strategy logic here
            return signals
"""

from .base import BaseStrategy, StrategyConfig, StrategyResult, StrategyType
from .registry import StrategyRegistry
from .backtesting import BacktestingEngine, BacktestConfig, BacktestResult
from .performance import PerformanceAnalyzer, PerformanceMetrics
from .optimization import (
    ParameterOptimizer, OptimizationConfig, OptimizationResult,
    ParameterRange, GridSearchOptimizer, RandomSearchOptimizer, GeneticAlgorithmOptimizer
)
from .ab_testing import (
    ABTestingEngine, ABTestConfig, ABTestResult, ABTestVariant,
    StatisticalTester
)
from .risk_analysis import (
    RiskAnalysisEngine, RiskMetrics, StressTestScenario, MonteCarloConfig,
    StressTestResult, RiskAnalysisResult, RiskCalculator, StressTester, MonteCarloSimulator
)

# RL components (conditional import due to optional dependencies)
# Note: RL modules are not imported by default to avoid loading large models
# Import them directly when needed: from .rl_environment import ...; from .rl_training import ...
_rl_available = False
try:
    import gym
    import stable_baselines3
    _rl_available = True
except ImportError:
    _rl_available = False

# RL classes are available only if dependencies are installed
if _rl_available:
    try:
        from .rl_environment import (
            TradingRLEnvironment, RLEnvironmentConfig, RLState, TechnicalIndicators
        )
        from .rl_training import (
            RLTrainingPipeline, RLTrainingConfig, TrainingResult, RLAgentManager
        )
    except ImportError:
        _rl_available = False
        TradingRLEnvironment = None
        RLTrainingPipeline = None
else:
    TradingRLEnvironment = None
    RLTrainingPipeline = None
    RLEnvironmentConfig = None
    RLState = None
    TechnicalIndicators = None
    RLTrainingPipeline = None
    RLTrainingConfig = None
    TrainingResult = None
    RLAgentManager = None

# Import concrete strategies for auto-discovery
from .moving_average import MovingAverageStrategy
from .mean_reversion import MeanReversionStrategy
from .momentum import MomentumStrategy

__all__ = [
    'BaseStrategy',
    'StrategyConfig',
    'StrategyResult',
    'StrategyType',
    'StrategyRegistry',
    # Backtesting
    'BacktestingEngine',
    'BacktestConfig',
    'BacktestResult',
    # Performance analysis
    'PerformanceAnalyzer',
    'PerformanceMetrics',
    # Parameter optimization
    'ParameterOptimizer',
    'OptimizationConfig',
    'OptimizationResult',
    'ParameterRange',
    'GridSearchOptimizer',
    'RandomSearchOptimizer',
    'GeneticAlgorithmOptimizer',
    # A/B testing
    'ABTestingEngine',
    'ABTestConfig',
    'ABTestResult',
    'ABTestVariant',
    'StatisticalTester',
    # Risk analysis
    'RiskAnalysisEngine',
    'RiskMetrics',
    'StressTestScenario',
    'MonteCarloConfig',
    'StressTestResult',
    'RiskAnalysisResult',
    'RiskCalculator',
    'StressTester',
    'MonteCarloSimulator',
    # Concrete strategies
    'MovingAverageStrategy',
    'MeanReversionStrategy',
    'MomentumStrategy',
]