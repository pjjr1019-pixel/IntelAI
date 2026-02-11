"""
rl_environment.py — Reinforcement Learning Environment for Trading Strategies.

Implements a Gym-compatible environment for training RL agents on trading strategies.
Provides state space, action space, and reward functions for autonomous trading.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

# Conditional imports for optional dependencies
try:
    import gym
    from gym import spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    # Create dummy classes for type hints
    class spaces:
        class Box:
            def __init__(self, low, high, shape, dtype): pass
        class MultiDiscrete:
            def __init__(self, nvec): pass
    class gym:
        class Env:
            pass

from ..market_data import MarketDataService
from ..trading_service import TradingService
from .base import SignalType, StrategyConfig, StrategyType

logger = logging.getLogger(__name__)


@dataclass
class RLEnvironmentConfig:
    """Configuration for the RL trading environment."""

    # Market data
    symbols: List[str] = field(default_factory=lambda: ["SPY", "QQQ", "IWM", "TLT", "GLD"])
    lookback_window: int = 20  # Days of historical data for state
    max_position_size: float = 0.1  # Max 10% of portfolio per position

    # Reward function
    reward_type: str = "sharpe_ratio"  # Options: sharpe_ratio, total_return, risk_adjusted
    risk_free_rate: float = 0.02  # Annual risk-free rate for Sharpe calculation

    # Episode settings
    episode_length_days: int = 252  # 1 year trading period
    transaction_cost_bps: int = 5  # 5 basis points per trade

    # State features
    include_technical_indicators: bool = True
    include_market_regime: bool = True
    include_portfolio_features: bool = True

    # Action space
    action_type: str = "discrete"  # discrete or continuous
    n_discrete_actions: int = 11  # -1.0 to 1.0 in 0.2 increments for position sizing


@dataclass
class RLState:
    """State representation for the RL environment."""

    # Market data features (technical indicators, returns, volatility)
    market_features: np.ndarray  # Shape: (n_symbols, n_features, lookback_window)

    # Portfolio state
    cash_balance: float
    portfolio_value: float
    current_positions: Dict[str, float]  # symbol -> position_size (% of portfolio)

    # Market regime indicators
    market_regime: str  # bull, bear, sideways

    # Risk metrics
    portfolio_volatility: float
    sharpe_ratio: float

    # Time information
    current_date: datetime
    days_remaining: int

    def to_array(self) -> np.ndarray:
        """Convert state to flat numpy array for neural networks."""
        # Flatten market features
        market_flat = self.market_features.flatten()

        # Portfolio features
        portfolio_features = np.array([
            self.cash_balance / self.portfolio_value,  # Cash ratio
            len(self.current_positions),  # Number of positions
            self.portfolio_volatility,
            self.sharpe_ratio,
            self.days_remaining / 252.0  # Normalized time remaining
        ])

        # Position features (one-hot encoded positions for each symbol)
        position_features = np.zeros(len(self.market_features))
        for i, symbol in enumerate(self.current_positions.keys()):
            if symbol in self.current_positions:
                position_features[i] = self.current_positions[symbol]

        # Market regime (one-hot encoded)
        regime_features = np.zeros(3)
        regime_map = {"bull": 0, "bear": 1, "sideways": 2}
        if self.market_regime in regime_map:
            regime_features[regime_map[self.market_regime]] = 1.0

        return np.concatenate([
            market_flat,
            portfolio_features,
            position_features,
            regime_features
        ])


class TradingRLEnvironment(gym.Env):
    """
    OpenAI Gym-compatible environment for training RL trading agents.

    State Space:
    - Market data features (technical indicators, returns, volatility)
    - Portfolio state (cash balance, positions, P&L)
    - Market regime indicators
    - Risk metrics

    Action Space:
    - Discrete: Position sizing decisions (-1.0 to 1.0 in steps)
    - Continuous: Direct position sizing commands

    Reward Function:
    - Sharpe ratio improvement
    - Risk-adjusted returns
    - Total portfolio returns with risk penalties
    """

    def __init__(
        self,
        config: RLEnvironmentConfig,
        market_data_service: MarketDataService,
        trading_service: TradingService,
        historical_data: pd.DataFrame
    ):
        if not GYM_AVAILABLE:
            raise ImportError("TradingRLEnvironment requires gym library. Install with: pip install gym[atari,accept-rom-license]")

        super().__init__()

        self.config = config
        self.market_data = market_data_service
        self.trading_service = trading_service
        self.historical_data = historical_data

        # Initialize state
        self.current_state: Optional[RLState] = None
        self.current_date: Optional[datetime] = None
        self.portfolio_value: float = 10000.0  # Starting capital
        self.cash_balance: float = self.portfolio_value
        self.positions: Dict[str, float] = {}
        self.episode_start_value: float = self.portfolio_value

        # Performance tracking
        self.portfolio_history: List[float] = [self.portfolio_value]
        self.action_history: List[Dict[str, Any]] = []

        # Define action and observation spaces
        self._define_spaces()

        # Technical indicator calculators
        self.indicators = TechnicalIndicators()

        logger.info(f"Initialized RL Trading Environment with {len(config.symbols)} symbols")

    def _define_spaces(self):
        """Define the action and observation spaces."""
        n_symbols = len(self.config.symbols)

        if self.config.action_type == "discrete":
            # Discrete actions: position sizing from -1.0 to 1.0 in steps
            self.action_space = spaces.MultiDiscrete([
                self.config.n_discrete_actions  # Position size for each symbol
            ] * n_symbols)
        else:
            # Continuous actions: direct position sizing
            self.action_space = spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(n_symbols,),
                dtype=np.float32
            )

        # Calculate observation space size
        market_features_size = n_symbols * self.config.lookback_window * 10  # 10 features per symbol per day
        portfolio_features_size = 5  # cash_ratio, n_positions, volatility, sharpe, time_remaining
        position_features_size = n_symbols  # current positions
        regime_features_size = 3  # bull/bear/sideways

        obs_size = (market_features_size + portfolio_features_size +
                   position_features_size + regime_features_size)

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_size,),
            dtype=np.float32
        )

    def reset(self) -> np.ndarray:
        """Reset the environment to initial state."""
        # Reset portfolio
        self.portfolio_value = 10000.0
        self.cash_balance = self.portfolio_value
        self.positions = {}
        self.episode_start_value = self.portfolio_value
        self.portfolio_history = [self.portfolio_value]
        self.action_history = []

        # Set start date (ensure we have enough historical data)
        start_date = self.historical_data.index.min() + timedelta(days=self.config.lookback_window)
        self.current_date = start_date

        # Initialize state
        self.current_state = self._get_state()

        logger.info(f"Environment reset. Starting date: {self.current_date}")
        return self.current_state.to_array()

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment.

        Args:
            action: Action to take (position sizes for each symbol)

        Returns:
            next_state, reward, done, info
        """
        # Convert action to position targets
        if self.config.action_type == "discrete":
            # Convert discrete actions to continuous position sizes
            position_targets = {}
            for i, symbol in enumerate(self.config.symbols):
                # Map discrete action to position size (-1.0 to 1.0)
                discrete_action = action[i]
                position_size = (discrete_action / (self.config.n_discrete_actions - 1)) * 2.0 - 1.0
                position_targets[symbol] = position_size
        else:
            # Continuous actions are direct position sizes
            position_targets = {symbol: action[i] for i, symbol in enumerate(self.config.symbols)}

        # Execute trades based on action
        reward, trade_info = self._execute_action(position_targets)

        # Update date
        self.current_date += timedelta(days=1)

        # Check if episode is done
        done = self._is_episode_done()

        # Get new state
        self.current_state = self._get_state()

        # Additional info
        info = {
            "portfolio_value": self.portfolio_value,
            "cash_balance": self.cash_balance,
            "positions": self.positions.copy(),
            "current_date": self.current_date,
            "trade_info": trade_info,
            "days_remaining": self._get_days_remaining()
        }

        return self.current_state.to_array(), reward, done, info

    def _execute_action(self, position_targets: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """Execute trading action and calculate reward."""
        old_portfolio_value = self.portfolio_value
        trades_executed = []

        # Get current prices
        current_prices = {}
        for symbol in self.config.symbols:
            try:
                price_data = self.historical_data.loc[self.current_date, symbol]
                if isinstance(price_data, pd.Series):
                    current_prices[symbol] = price_data['close']
                else:
                    current_prices[symbol] = price_data
            except KeyError:
                # Use last available price if current date not available
                available_data = self.historical_data[self.historical_data.index <= self.current_date]
                if not available_data.empty:
                    last_data = available_data.iloc[-1]
                    if isinstance(last_data, pd.Series):
                        current_prices[symbol] = last_data[symbol]['close'] if symbol in last_data else last_data.get('close', 100.0)
                    else:
                        current_prices[symbol] = last_data
                else:
                    current_prices[symbol] = 100.0  # Fallback price

        # Execute trades for each symbol
        for symbol, target_position in position_targets.items():
            current_position = self.positions.get(symbol, 0.0)
            position_change = target_position - current_position

            if abs(position_change) > 0.01:  # Minimum trade threshold
                price = current_prices.get(symbol, 100.0)
                trade_value = abs(position_change) * self.portfolio_value
                shares = trade_value / price

                # Apply transaction costs
                commission = trade_value * (self.config.transaction_cost_bps / 10000.0)

                if position_change > 0:  # Buy
                    cost = (shares * price) + commission
                    if self.cash_balance >= cost:
                        self.cash_balance -= cost
                        self.positions[symbol] = target_position
                        trades_executed.append({
                            "symbol": symbol,
                            "action": "buy",
                            "shares": shares,
                            "price": price,
                            "value": trade_value,
                            "commission": commission
                        })
                else:  # Sell
                    proceeds = (shares * price) - commission
                    self.cash_balance += proceeds
                    self.positions[symbol] = target_position
                    trades_executed.append({
                        "symbol": symbol,
                        "action": "sell",
                        "shares": shares,
                        "price": price,
                        "value": trade_value,
                        "commission": commission
                    })

        # Update portfolio value
        position_value = sum(
            abs(pos) * self.portfolio_value * current_prices.get(symbol, 100.0) / 100.0
            for symbol, pos in self.positions.items()
        )
        self.portfolio_value = self.cash_balance + position_value
        self.portfolio_history.append(self.portfolio_value)

        # Calculate reward
        reward = self._calculate_reward(old_portfolio_value)

        trade_info = {
            "trades_executed": len(trades_executed),
            "total_commission": sum(t.get("commission", 0) for t in trades_executed),
            "portfolio_return": (self.portfolio_value - old_portfolio_value) / old_portfolio_value
        }

        return reward, trade_info

    def _calculate_reward(self, old_portfolio_value: float) -> float:
        """Calculate reward based on portfolio performance."""
        if self.config.reward_type == "total_return":
            # Simple total return
            reward = (self.portfolio_value - old_portfolio_value) / old_portfolio_value

        elif self.config.reward_type == "sharpe_ratio":
            # Sharpe ratio based reward
            if len(self.portfolio_history) >= 30:  # Need enough data for meaningful calculation
                returns = np.diff(np.log(self.portfolio_history[-30:]))
                if len(returns) > 0 and np.std(returns) > 0:
                    sharpe = (np.mean(returns) - self.config.risk_free_rate/252) / np.std(returns)
                    reward = sharpe * 0.01  # Scale down for reasonable reward values
                else:
                    reward = 0.0
            else:
                reward = (self.portfolio_value - old_portfolio_value) / old_portfolio_value

        elif self.config.reward_type == "risk_adjusted":
            # Risk-adjusted return with penalties for volatility
            daily_return = (self.portfolio_value - old_portfolio_value) / old_portfolio_value
            if len(self.portfolio_history) >= 10:
                recent_returns = np.diff(np.log(self.portfolio_history[-10:]))
                volatility_penalty = np.std(recent_returns) * 2.0  # Penalty for volatility
                reward = daily_return - volatility_penalty
            else:
                reward = daily_return

        else:
            reward = (self.portfolio_value - old_portfolio_value) / old_portfolio_value

        return float(reward)

    def _get_state(self) -> RLState:
        """Construct the current state representation."""
        # Get market features
        market_features = self._get_market_features()

        # Calculate portfolio metrics
        portfolio_volatility = self._calculate_portfolio_volatility()
        sharpe_ratio = self._calculate_sharpe_ratio()

        # Determine market regime
        market_regime = self._determine_market_regime()

        return RLState(
            market_features=market_features,
            cash_balance=self.cash_balance,
            portfolio_value=self.portfolio_value,
            current_positions=self.positions.copy(),
            market_regime=market_regime,
            portfolio_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            current_date=self.current_date,
            days_remaining=self._get_days_remaining()
        )

    def _get_market_features(self) -> np.ndarray:
        """Extract market features for state representation."""
        n_symbols = len(self.config.symbols)
        lookback = self.config.lookback_window

        # Initialize feature array
        features = np.zeros((n_symbols, 10, lookback))  # 10 features per symbol per day

        for i, symbol in enumerate(self.config.symbols):
            # Get historical data for this symbol
            end_date = self.current_date
            start_date = end_date - timedelta(days=lookback)

            symbol_data = self.historical_data[
                (self.historical_data.index >= start_date) &
                (self.historical_data.index <= end_date)
            ]

            if len(symbol_data) == 0:
                continue

            # Extract price data
            if hasattr(symbol_data, symbol):
                price_data = symbol_data[symbol]
            else:
                price_data = symbol_data

            # Calculate technical indicators
            if self.config.include_technical_indicators and len(price_data) >= lookback:
                try:
                    close_prices = price_data['close'].values[-lookback:] if 'close' in price_data.columns else price_data.values[-lookback:]
                    high_prices = price_data['high'].values[-lookback:] if 'high' in price_data.columns else close_prices
                    low_prices = price_data['low'].values[-lookback:] if 'low' in price_data.columns else close_prices
                    volume = price_data['volume'].values[-lookback:] if 'volume' in price_data.columns else np.ones(lookback)

                    # Feature 0: Normalized close price
                    features[i, 0, :] = self.indicators.normalize_prices(close_prices)

                    # Feature 1: Daily returns
                    features[i, 1, :] = self.indicators.calculate_returns(close_prices)

                    # Feature 2: SMA(5)
                    features[i, 2, :] = self.indicators.sma(close_prices, 5)

                    # Feature 3: SMA(20)
                    features[i, 3, :] = self.indicators.sma(close_prices, 20)

                    # Feature 4: RSI(14)
                    features[i, 4, :] = self.indicators.rsi(close_prices, 14)

                    # Feature 5: MACD
                    features[i, 5, :] = self.indicators.macd(close_prices)

                    # Feature 6: Bollinger Bands position
                    features[i, 6, :] = self.indicators.bollinger_position(close_prices)

                    # Feature 7: Volume normalized
                    features[i, 7, :] = self.indicators.normalize_volume(volume)

                    # Feature 8: Price volatility (20-day)
                    features[i, 8, :] = self.indicators.volatility(close_prices, 20)

                    # Feature 9: Trend strength
                    features[i, 9, :] = self.indicators.trend_strength(close_prices, 20)

                except Exception as e:
                    logger.warning(f"Error calculating indicators for {symbol}: {e}")
                    # Fill with zeros on error
                    pass

        return features

    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility."""
        if len(self.portfolio_history) < 10:
            return 0.0

        returns = np.diff(np.log(self.portfolio_history[-30:]))  # Last 30 days
        return float(np.std(returns)) if len(returns) > 0 else 0.0

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio."""
        if len(self.portfolio_history) < 10:
            return 0.0

        returns = np.diff(np.log(self.portfolio_history[-60:]))  # Last 60 days
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0

        excess_returns = returns - self.config.risk_free_rate / 252
        return float(np.mean(excess_returns) / np.std(returns))

    def _determine_market_regime(self) -> str:
        """Determine current market regime."""
        if len(self.portfolio_history) < 20:
            return "sideways"

        # Simple regime detection based on recent performance
        recent_returns = np.diff(np.log(self.portfolio_history[-20:]))
        avg_return = np.mean(recent_returns)
        volatility = np.std(recent_returns)

        if avg_return > 0.001 and volatility < 0.02:  # Bull market
            return "bull"
        elif avg_return < -0.001 and volatility > 0.03:  # Bear market
            return "bear"
        else:
            return "sideways"

    def _get_days_remaining(self) -> int:
        """Get days remaining in episode."""
        if not self.current_date:
            return self.config.episode_length_days

        episode_end = self.current_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=self.config.episode_length_days)
        days_remaining = (episode_end - self.current_date).days
        return max(0, days_remaining)

    def _is_episode_done(self) -> bool:
        """Check if episode should end."""
        if not self.current_date:
            return True

        # End if we've reached the episode length
        days_elapsed = (self.current_date - (self.historical_data.index.min() + timedelta(days=self.config.lookback_window))).days
        if days_elapsed >= self.config.episode_length_days:
            return True

        # End if portfolio is wiped out
        if self.portfolio_value < 100.0:  # Less than $100 remaining
            return True

        # End if we've reached the end of available data
        if self.current_date >= self.historical_data.index.max():
            return True

        return False

    def render(self, mode: str = "human"):
        """Render the environment state."""
        if self.current_state is None:
            return

        print(f"Date: {self.current_state.current_date}")
        print(".2f")
        print(".2f")
        print(f"Positions: {len(self.current_state.current_positions)}")
        print(".4f")
        print(f"Market Regime: {self.current_state.market_regime}")
        print(f"Days Remaining: {self.current_state.days_remaining}")


class TechnicalIndicators:
    """Technical indicator calculations for market features."""

    def normalize_prices(self, prices: np.ndarray) -> np.ndarray:
        """Normalize prices to 0-1 scale."""
        if len(prices) == 0:
            return np.array([])
        min_price = np.min(prices)
        max_price = np.max(prices)
        if max_price == min_price:
            return np.zeros(len(prices))
        return (prices - min_price) / (max_price - min_price)

    def calculate_returns(self, prices: np.ndarray) -> np.ndarray:
        """Calculate daily returns."""
        if len(prices) < 2:
            return np.zeros(len(prices))
        returns = np.diff(prices) / prices[:-1]
        return np.concatenate([[0], returns])  # Pad with zero for first day

    def sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Simple Moving Average."""
        if len(prices) < period:
            return np.zeros(len(prices))
        sma = np.convolve(prices, np.ones(period)/period, mode='valid')
        return np.concatenate([np.zeros(period-1), sma])

    def rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        if len(prices) < period + 1:
            return np.zeros(len(prices))

        returns = np.diff(prices)
        gains = np.where(returns > 0, returns, 0)
        losses = np.where(returns < 0, -returns, 0)

        avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')

        rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
        rsi = 100 - (100 / (1 + rs))

        return np.concatenate([np.zeros(period), rsi])

    def macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> np.ndarray:
        """MACD indicator."""
        if len(prices) < slow:
            return np.zeros(len(prices))

        fast_sma = self.sma(prices, fast)
        slow_sma = self.sma(prices, slow)
        macd_line = fast_sma - slow_sma

        signal_line = self.sma(macd_line, signal)
        macd = macd_line - signal_line

        return macd

    def bollinger_position(self, prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Position within Bollinger Bands (-1 to 1)."""
        if len(prices) < period:
            return np.zeros(len(prices))

        sma = self.sma(prices, period)
        std = np.array([np.std(prices[max(0, i-period+1):i+1]) for i in range(len(prices))])

        upper_band = sma + 2 * std
        lower_band = sma - 2 * std

        # Position within bands
        band_width = upper_band - lower_band
        position = 2 * (prices - sma) / (band_width + 1e-10)  # -1 to 1

        return np.clip(position, -1, 1)

    def normalize_volume(self, volume: np.ndarray) -> np.ndarray:
        """Normalize volume to 0-1 scale."""
        if len(volume) == 0 or np.max(volume) == 0:
            return np.array([])
        return volume / np.max(volume)

    def volatility(self, prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling volatility."""
        if len(prices) < period:
            return np.zeros(len(prices))

        returns = self.calculate_returns(prices)
        volatility = np.array([np.std(returns[max(0, i-period+1):i+1]) for i in range(len(returns))])

        return volatility

    def trend_strength(self, prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Trend strength indicator (-1 to 1)."""
        if len(prices) < period:
            return np.zeros(len(prices))

        # Linear regression slope normalized
        trend_strength = np.zeros(len(prices))

        for i in range(period-1, len(prices)):
            y = prices[i-period+1:i+1]
            x = np.arange(len(y))
            slope = np.polyfit(x, y, 1)[0]

            # Normalize by average price
            avg_price = np.mean(y)
            normalized_slope = slope / (avg_price + 1e-10)
            trend_strength[i] = np.clip(normalized_slope * 100, -1, 1)  # Scale and clip

        return trend_strength