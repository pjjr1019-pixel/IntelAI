"""
rl_training.py — Reinforcement Learning Training Pipeline for Trading Agents.

Implements training infrastructure for RL agents including:
- Agent architectures (DQN, PPO, A2C)
- Training loops and curriculum learning
- Performance evaluation and validation
- Model serialization and deployment
"""

import logging
import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
import numpy as np
import pandas as pd

# Conditional imports for optional dependencies
try:
    import gym
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    class gym:
        class Env:
            pass

try:
    from stable_baselines3 import PPO, A2C, DQN
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.results_plotter import plot_results
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    # Create dummy classes
    class PPO: pass
    class A2C: pass
    class DQN: pass
    class BaseCallback: pass
    class Monitor: pass
    class DummyVecEnv: pass
    class VecNormalize: pass

from .rl_environment import TradingRLEnvironment, RLEnvironmentConfig
from ..market_data import MarketDataService
from ..trading_service import TradingService

logger = logging.getLogger(__name__)


@dataclass
class RLTrainingConfig:
    """Configuration for RL agent training."""

    # Algorithm selection
    algorithm: str = "ppo"  # ppo, a2c, dqn

    # Training parameters
    total_timesteps: int = 1000000
    learning_rate: float = 3e-4
    batch_size: int = 64
    n_epochs: int = 10

    # PPO specific
    n_steps: int = 2048
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.0
    vf_coef: float = 0.5

    # A2C specific
    n_steps_a2c: int = 5

    # DQN specific
    buffer_size: int = 100000
    learning_starts: int = 1000
    target_update_interval: int = 1000
    exploration_fraction: float = 0.1

    # Environment parameters
    n_envs: int = 1
    normalize_env: bool = True

    # Evaluation
    eval_freq: int = 10000
    n_eval_episodes: int = 10

    # Curriculum learning
    curriculum_learning: bool = True
    difficulty_levels: List[str] = field(default_factory=lambda: ["easy", "medium", "hard"])

    # Model saving
    save_freq: int = 50000
    model_save_path: str = "models/rl_agents"

    # Logging
    log_interval: int = 1000
    verbose: int = 1


@dataclass
class TrainingResult:
    """Results from RL training."""

    agent: Any  # Trained RL agent
    training_config: RLTrainingConfig
    environment_config: RLEnvironmentConfig

    # Performance metrics
    final_reward: float
    best_reward: float
    training_time_seconds: float
    total_episodes: int

    # Evaluation results
    eval_rewards: List[float]
    eval_portfolio_returns: List[float]
    eval_sharpe_ratios: List[float]

    # Model metadata
    model_path: Optional[str] = None
    training_date: datetime = field(default_factory=datetime.now)

    def save(self, path: str):
        """Save training result to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Save model separately
        model_path = f"{path}_model"
        self.agent.save(model_path)
        self.model_path = model_path

        # Save metadata (excluding the agent object)
        metadata = {
            "training_config": self.training_config,
            "environment_config": self.environment_config,
            "final_reward": self.final_reward,
            "best_reward": self.best_reward,
            "training_time_seconds": self.training_time_seconds,
            "total_episodes": self.total_episodes,
            "eval_rewards": self.eval_rewards,
            "eval_portfolio_returns": self.eval_portfolio_returns,
            "eval_sharpe_ratios": self.eval_sharpe_ratios,
            "model_path": self.model_path,
            "training_date": self.training_date
        }

        with open(f"{path}_metadata.pkl", 'wb') as f:
            pickle.dump(metadata, f)

    @classmethod
    def load(cls, path: str) -> "TrainingResult":
        """Load training result from disk."""
        if not SB3_AVAILABLE:
            raise ImportError("TrainingResult.load requires stable-baselines3. Install with: pip install stable-baselines3")

        # Load metadata
        with open(f"{path}_metadata.pkl", 'rb') as f:
            metadata = pickle.load(f)

        # Load model
        if metadata["algorithm"] == "ppo":
            agent = PPO.load(metadata["model_path"])
        elif metadata["algorithm"] == "a2c":
            agent = A2C.load(metadata["model_path"])
        elif metadata["algorithm"] == "dqn":
            agent = DQN.load(metadata["model_path"])
        else:
            raise ValueError(f"Unknown algorithm: {metadata['algorithm']}")

        # Reconstruct object
        result = cls(
            agent=agent,
            training_config=metadata["training_config"],
            environment_config=metadata["environment_config"],
            final_reward=metadata["final_reward"],
            best_reward=metadata["best_reward"],
            training_time_seconds=metadata["training_time_seconds"],
            total_episodes=metadata["total_episodes"],
            eval_rewards=metadata["eval_rewards"],
            eval_portfolio_returns=metadata["eval_portfolio_returns"],
            eval_sharpe_ratios=metadata["eval_sharpe_ratios"],
            model_path=metadata["model_path"],
            training_date=metadata["training_date"]
        )

        return result


class RLTrainingPipeline:
    """
    Complete training pipeline for RL trading agents.

    Handles environment setup, agent training, evaluation, and deployment.
    """

    def __init__(
        self,
        market_data_service: MarketDataService,
        trading_service: TradingService,
        historical_data: pd.DataFrame
    ):
        if not GYM_AVAILABLE:
            raise ImportError("RLTrainingPipeline requires gym library. Install with: pip install gym[atari,accept-rom-license]")

        if not SB3_AVAILABLE:
            raise ImportError("RLTrainingPipeline requires stable-baselines3. Install with: pip install stable-baselines3")

        self.market_data = market_data_service
        self.trading_service = trading_service
        self.historical_data = historical_data

        # Training state
        self.current_agent = None
        self.training_results: List[TrainingResult] = []

        logger.info("Initialized RL Training Pipeline")

    def create_environment(
        self,
        config: RLEnvironmentConfig,
        normalize: bool = True
    ) -> gym.Env:
        """Create and optionally normalize the RL environment."""

        def make_env():
            env = TradingRLEnvironment(
                config=config,
                market_data_service=self.market_data,
                trading_service=self.trading_service,
                historical_data=self.historical_data
            )
            return env

        if config.action_type == "discrete":
            env = DummyVecEnv([make_env])
        else:
            env = make_env()

        if normalize:
            env = VecNormalize(env, norm_obs=True, norm_reward=True)

        return env

    def create_agent(
        self,
        algorithm: str,
        env: gym.Env,
        config: RLTrainingConfig
    ) -> Any:
        """Create RL agent based on algorithm selection."""

        if algorithm.lower() == "ppo":
            agent = PPO(
                "MlpPolicy",
                env,
                learning_rate=config.learning_rate,
                n_steps=config.n_steps,
                batch_size=config.batch_size,
                n_epochs=config.n_epochs,
                gamma=config.gamma,
                gae_lambda=config.gae_lambda,
                clip_range=config.clip_range,
                ent_coef=config.ent_coef,
                vf_coef=config.vf_coef,
                verbose=config.verbose
            )

        elif algorithm.lower() == "a2c":
            agent = A2C(
                "MlpPolicy",
                env,
                learning_rate=config.learning_rate,
                n_steps=config.n_steps_a2c,
                gamma=config.gamma,
                gae_lambda=config.gae_lambda,
                ent_coef=config.ent_coef,
                vf_coef=config.vf_coef,
                verbose=config.verbose
            )

        elif algorithm.lower() == "dqn":
            agent = DQN(
                "MlpPolicy",
                env,
                learning_rate=config.learning_rate,
                buffer_size=config.buffer_size,
                learning_starts=config.learning_starts,
                batch_size=config.batch_size,
                gamma=config.gamma,
                target_update_interval=config.target_update_interval,
                exploration_fraction=config.exploration_fraction,
                verbose=config.verbose
            )

        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        return agent

    def train_agent(
        self,
        training_config: RLTrainingConfig,
        environment_config: RLEnvironmentConfig,
        model_name: str = "trading_agent"
    ) -> TrainingResult:
        """
        Train an RL agent with the specified configuration.

        Args:
            training_config: Training hyperparameters
            environment_config: Environment configuration
            model_name: Name for saving the trained model

        Returns:
            TrainingResult with trained agent and performance metrics
        """
        if not GYM_AVAILABLE:
            raise ImportError("RLTrainingPipeline.train_agent requires gym library. Install with: pip install gym[atari,accept-rom-license]")

        if not SB3_AVAILABLE:
            raise ImportError("RLTrainingPipeline.train_agent requires stable-baselines3. Install with: pip install stable-baselines3")

        import time
        start_time = time.time()

        logger.info(f"Starting RL training with {training_config.algorithm.upper()} algorithm")
        logger.info(f"Total timesteps: {training_config.total_timesteps}")

        # Create environment
        env = self.create_environment(environment_config, training_config.normalize_env)

        # Create agent
        agent = self.create_agent(training_config.algorithm, env, training_config)

        # Setup callbacks
        callbacks = []
        if training_config.save_freq > 0:
            save_path = Path(training_config.model_save_path) / model_name
            save_path.parent.mkdir(parents=True, exist_ok=True)

            save_callback = SaveModelCallback(
                save_freq=training_config.save_freq,
                save_path=str(save_path)
            )
            callbacks.append(save_callback)

        # Training with curriculum learning if enabled
        if training_config.curriculum_learning:
            self._train_with_curriculum(agent, training_config, environment_config, callbacks)
        else:
            agent.learn(
                total_timesteps=training_config.total_timesteps,
                callback=callbacks if callbacks else None,
                log_interval=training_config.log_interval
            )

        training_time = time.time() - start_time

        # Evaluate final agent
        eval_results = self.evaluate_agent(agent, environment_config, training_config.n_eval_episodes)

        # Create training result
        result = TrainingResult(
            agent=agent,
            training_config=training_config,
            environment_config=environment_config,
            final_reward=np.mean(eval_results["rewards"]),
            best_reward=np.max(eval_results["rewards"]),
            training_time_seconds=training_time,
            total_episodes=training_config.total_timesteps // training_config.n_steps if training_config.algorithm == "ppo" else training_config.total_timesteps // 1000,
            eval_rewards=eval_results["rewards"],
            eval_portfolio_returns=eval_results["portfolio_returns"],
            eval_sharpe_ratios=eval_results["sharpe_ratios"]
        )

        # Save result
        save_path = Path(training_config.model_save_path) / f"{model_name}_result"
        result.save(str(save_path))

        self.training_results.append(result)
        self.current_agent = agent

        logger.info(".2f")
        logger.info(".4f")
        logger.info(".2f")

        return result

    def _train_with_curriculum(
        self,
        agent: Any,
        training_config: RLTrainingConfig,
        environment_config: RLEnvironmentConfig,
        callbacks: List[BaseCallback]
    ):
        """Train agent with curriculum learning (progressive difficulty)."""

        total_timesteps = training_config.total_timesteps
        timesteps_per_level = total_timesteps // len(training_config.difficulty_levels)

        for level in training_config.difficulty_levels:
            logger.info(f"Training curriculum level: {level}")

            # Adjust environment difficulty
            level_config = self._adjust_config_for_level(environment_config, level)

            # Create new environment for this level
            env = self.create_environment(level_config, training_config.normalize_env)

            # Update agent's environment
            agent.set_env(env)

            # Train on this level
            agent.learn(
                total_timesteps=timesteps_per_level,
                callback=callbacks if callbacks else None,
                log_interval=training_config.log_interval,
                reset_num_timesteps=False  # Continue training
            )

    def _adjust_config_for_level(
        self,
        config: RLEnvironmentConfig,
        level: str
    ) -> RLEnvironmentConfig:
        """Adjust environment config based on curriculum level."""

        new_config = RLEnvironmentConfig(**config.__dict__)

        if level == "easy":
            new_config.transaction_cost_bps = 1  # Lower costs
            new_config.episode_length_days = 126  # Shorter episodes
            new_config.max_position_size = 0.05  # Smaller positions

        elif level == "medium":
            new_config.transaction_cost_bps = 5  # Normal costs
            new_config.episode_length_days = 252  # Standard episodes
            new_config.max_position_size = 0.1  # Normal positions

        elif level == "hard":
            new_config.transaction_cost_bps = 10  # Higher costs
            new_config.episode_length_days = 504  # Longer episodes
            new_config.max_position_size = 0.2  # Larger positions

        return new_config

    def evaluate_agent(
        self,
        agent: Any,
        environment_config: RLEnvironmentConfig,
        n_episodes: int = 10
    ) -> Dict[str, List[float]]:
        """
        Evaluate trained agent performance.

        Returns dict with rewards, portfolio returns, and Sharpe ratios.
        """
        env = self.create_environment(environment_config, normalize=False)

        rewards = []
        portfolio_returns = []
        sharpe_ratios = []

        for episode in range(n_episodes):
            obs = env.reset()
            episode_reward = 0
            done = False
            step_count = 0

            portfolio_values = []

            while not done and step_count < environment_config.episode_length_days:
                action, _ = agent.predict(obs, deterministic=True)
                obs, reward, done, info = env.step(action)

                episode_reward += reward
                step_count += 1

                if "portfolio_value" in info:
                    portfolio_values.append(info["portfolio_value"])

            rewards.append(episode_reward)

            # Calculate portfolio metrics
            if len(portfolio_values) > 1:
                initial_value = portfolio_values[0]
                final_value = portfolio_values[-1]
                total_return = (final_value - initial_value) / initial_value
                portfolio_returns.append(total_return)

                # Calculate Sharpe ratio
                if len(portfolio_values) > 10:
                    returns = np.diff(np.log(portfolio_values))
                    if np.std(returns) > 0:
                        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
                        sharpe_ratios.append(sharpe)
                    else:
                        sharpe_ratios.append(0.0)
                else:
                    sharpe_ratios.append(0.0)
            else:
                portfolio_returns.append(0.0)
                sharpe_ratios.append(0.0)

        env.close()

        return {
            "rewards": rewards,
            "portfolio_returns": portfolio_returns,
            "sharpe_ratios": sharpe_ratios
        }

    def load_agent(self, model_path: str, algorithm: str) -> Any:
        """Load a trained agent from disk."""

        if algorithm.lower() == "ppo":
            agent = PPO.load(model_path)
        elif algorithm.lower() == "a2c":
            agent = A2C.load(model_path)
        elif algorithm.lower() == "dqn":
            agent = DQN.load(model_path)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        self.current_agent = agent
        logger.info(f"Loaded {algorithm.upper()} agent from {model_path}")

        return agent

    def create_trading_strategy_from_agent(
        self,
        agent: Any,
        environment_config: RLEnvironmentConfig,
        strategy_name: str = "RL_Trading_Agent"
    ) -> Any:
        """
        Create a trading strategy that uses the trained RL agent.

        This allows the RL agent to be used within the existing strategy framework.
        """
        from .base import StrategyConfig, StrategyType

        # Create strategy config
        config = StrategyConfig(
            strategy_id=f"rl_{strategy_name.lower().replace(' ', '_')}",
            name=strategy_name,
            description=f"Reinforcement Learning trading agent ({environment_config.reward_type} reward)",
            strategy_type=StrategyType.MACHINE_LEARNING,
            symbols=environment_config.symbols,
            parameters={
                "agent": agent,
                "environment_config": environment_config,
                "algorithm": type(agent).__name__
            }
        )

        # Create RL strategy wrapper
        strategy = RLTradingStrategy(config, agent, environment_config)

        return strategy


class RLTradingStrategy:
    """
    Trading strategy that wraps a trained RL agent.

    Allows RL agents to be used within the existing strategy framework.
    """

    def __init__(
        self,
        config: Any,  # StrategyConfig
        agent: Any,
        environment_config: RLEnvironmentConfig
    ):
        self.config = config
        self.agent = agent
        self.env_config = environment_config

        # State tracking for the agent
        self.current_state = None
        self.portfolio_state = {
            "cash_balance": 10000.0,
            "portfolio_value": 10000.0,
            "positions": {}
        }

    async def generate_signals(self, market_data, portfolio) -> List[Any]:
        """Generate signals using the RL agent."""
        # This would need to be implemented to interface with the existing strategy framework
        # For now, return empty signals
        return []

    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "algorithm": type(self.agent).__name__,
            "reward_type": self.env_config.reward_type,
            "symbols": self.env_config.symbols
        }


class SaveModelCallback(BaseCallback):
    """Callback for saving models during training."""

    def __init__(self, save_freq: int, save_path: str, verbose: int = 0):
        super().__init__(verbose)
        self.save_freq = save_freq
        self.save_path = save_path

    def _on_step(self) -> bool:
        if self.n_calls % self.save_freq == 0:
            model_path = f"{self.save_path}_{self.n_calls}"
            self.model.save(model_path)

            if self.verbose > 0:
                print(f"Saved model to {model_path}")

        return True


class RLAgentManager:
    """
    Manager for multiple RL agents with performance tracking and selection.
    """

    def __init__(self, model_dir: str = "models/rl_agents"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.agents: Dict[str, Dict[str, Any]] = {}
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}

    def register_agent(
        self,
        name: str,
        agent: Any,
        config: RLTrainingConfig,
        performance_metrics: Dict[str, Any]
    ):
        """Register a trained agent."""

        self.agents[name] = {
            "agent": agent,
            "config": config,
            "performance": performance_metrics,
            "registered_date": datetime.now()
        }

        # Initialize performance history
        self.performance_history[name] = [performance_metrics]

        logger.info(f"Registered RL agent: {name}")

    def get_best_agent(self, metric: str = "sharpe_ratio") -> Tuple[str, Any]:
        """Get the best performing agent by specified metric."""

        if not self.agents:
            raise ValueError("No agents registered")

        best_agent = None
        best_score = float('-inf')

        for name, data in self.agents.items():
            score = data["performance"].get(metric, 0)
            if score > best_score:
                best_score = score
                best_agent = name

        return best_agent, self.agents[best_agent]["agent"]

    def update_performance(self, name: str, new_metrics: Dict[str, Any]):
        """Update performance metrics for an agent."""

        if name not in self.agents:
            raise ValueError(f"Agent {name} not registered")

        self.agents[name]["performance"] = new_metrics
        self.performance_history[name].append({
            **new_metrics,
            "timestamp": datetime.now()
        })

        logger.info(f"Updated performance for agent {name}")

    def save_agents(self):
        """Save all registered agents to disk."""

        for name, data in self.agents.items():
            agent_path = self.model_dir / f"{name}_agent"
            config_path = self.model_dir / f"{name}_config.pkl"

            # Save agent
            data["agent"].save(str(agent_path))

            # Save config and metadata
            metadata = {
                "config": data["config"],
                "performance": data["performance"],
                "registered_date": data["registered_date"]
            }

            with open(config_path, 'wb') as f:
                pickle.dump(metadata, f)

        logger.info(f"Saved {len(self.agents)} agents to {self.model_dir}")

    def load_agents(self):
        """Load all agents from disk."""

        for config_file in self.model_dir.glob("*_config.pkl"):
            name = config_file.stem.replace("_config", "")

            try:
                # Load metadata
                with open(config_file, 'rb') as f:
                    metadata = pickle.load(f)

                # Load agent
                agent_path = self.model_dir / f"{name}_agent.zip"
                if metadata["config"].algorithm.lower() == "ppo":
                    agent = PPO.load(str(agent_path))
                elif metadata["config"].algorithm.lower() == "a2c":
                    agent = A2C.load(str(agent_path))
                elif metadata["config"].algorithm.lower() == "dqn":
                    agent = DQN.load(str(agent_path))

                # Register agent
                self.register_agent(name, agent, metadata["config"], metadata["performance"])

            except Exception as e:
                logger.warning(f"Failed to load agent {name}: {e}")

        logger.info(f"Loaded {len(self.agents)} agents from {self.model_dir}")