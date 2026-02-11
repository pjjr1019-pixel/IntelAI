"""
registry.py — Strategy registry for discovery and management.

Provides centralized management of trading strategies with automatic
discovery, registration, and instantiation capabilities.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import BaseStrategy, StrategyConfig, StrategyType

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Registry for trading strategies.

    Manages strategy discovery, registration, and instantiation.
    Automatically discovers strategies from the strategies package.
    """

    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._configs: Dict[str, StrategyConfig] = {}
        self._discover_strategies()

    def _discover_strategies(self) -> None:
        """Automatically discover and register strategies from the package."""
        try:
            # Import the strategies package
            import vanguard_signal.strategies as strategies_pkg

            # Get the package path
            package_path = Path(strategies_pkg.__file__).parent

            # Discover all strategy modules
            for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
                if module_name not in ['base', 'registry', '__init__', 'risk_analysis', 'rl_environment', 'rl_training']:
                    try:
                        # Import the module
                        module = importlib.import_module(
                            f'vanguard_signal.strategies.{module_name}'
                        )

                        # Find strategy classes
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and
                                issubclass(obj, BaseStrategy) and
                                obj != BaseStrategy):
                                self.register_strategy(obj)

                    except Exception as e:
                        logger.warning(f"Failed to load strategy module {module_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to discover strategies: {e}")

    def register_strategy(self, strategy_class: Type[BaseStrategy]) -> None:
        """
        Register a strategy class.

        Args:
            strategy_class: The strategy class to register
        """
        strategy_id = getattr(strategy_class, 'STRATEGY_ID', None)
        if not strategy_id:
            # Generate ID from class name
            strategy_id = strategy_class.__name__.lower()

        if strategy_id in self._strategies:
            logger.warning(f"Strategy {strategy_id} already registered, overwriting")

        self._strategies[strategy_id] = strategy_class
        logger.info(f"Registered strategy: {strategy_id}")

    def unregister_strategy(self, strategy_id: str) -> None:
        """
        Unregister a strategy.

        Args:
            strategy_id: ID of the strategy to unregister
        """
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            if strategy_id in self._configs:
                del self._configs[strategy_id]
            logger.info(f"Unregistered strategy: {strategy_id}")

    def get_strategy_class(self, strategy_id: str) -> Optional[Type[BaseStrategy]]:
        """
        Get a strategy class by ID.

        Args:
            strategy_id: ID of the strategy

        Returns:
            Strategy class or None if not found
        """
        return self._strategies.get(strategy_id)

    def get_available_strategies(self) -> List[str]:
        """
        Get list of available strategy IDs.

        Returns:
            List of strategy IDs
        """
        return list(self._strategies.keys())

    def get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """
        Get information about a strategy.

        Args:
            strategy_id: ID of the strategy

        Returns:
            Dictionary with strategy information or None if not found
        """
        strategy_class = self.get_strategy_class(strategy_id)
        if not strategy_class:
            return None

        # Create a temporary instance to get metadata
        try:
            # Create minimal config for metadata extraction
            config = StrategyConfig(
                strategy_id=strategy_id,
                name=strategy_class.__name__,
                description=getattr(strategy_class, '__doc__', ''),
            )
            instance = strategy_class(config)

            return {
                'id': strategy_id,
                'name': getattr(strategy_class, 'STRATEGY_NAME', config.name.replace('Strategy', '').strip()),
                'description': config.description,
                'type': getattr(strategy_class, 'STRATEGY_TYPE', StrategyType.TREND_FOLLOWING).value,
                'version': getattr(strategy_class, 'VERSION', '1.0.0'),
                'author': getattr(strategy_class, 'AUTHOR', 'Unknown'),
                'parameters': instance.get_parameters(),
            }
        except Exception as e:
            logger.error(f"Failed to get info for strategy {strategy_id}: {e}")
            return None

    def create_strategy(
        self,
        strategy_id: str,
        config: Optional[StrategyConfig] = None
    ) -> Optional[BaseStrategy]:
        """
        Create an instance of a strategy.

        Args:
            strategy_id: ID of the strategy to create
            config: Strategy configuration (optional)

        Returns:
            Strategy instance or None if creation failed
        """
        strategy_class = self.get_strategy_class(strategy_id)
        if not strategy_class:
            logger.error(f"Strategy {strategy_id} not found")
            return None

        try:
            if config is None:
                # Create default config
                config = StrategyConfig(
                    strategy_id=strategy_id,
                    name=strategy_class.__name__,
                    description=getattr(strategy_class, '__doc__', ''),
                )

            instance = strategy_class(config)

            # Validate configuration
            errors = instance.validate_config()
            if errors:
                logger.error(f"Invalid config for strategy {strategy_id}: {errors}")
                return None

            return instance

        except Exception as e:
            logger.error(f"Failed to create strategy {strategy_id}: {e}")
            return None

    def list_strategies(self) -> List[str]:
        """
        List all available strategy IDs.

        Returns:
            List of all strategy IDs
        """
        return list(self._strategies.keys())
        """
        List strategies of a specific type.

        Args:
            strategy_type: Type of strategies to list

        Returns:
            List of strategy IDs of the specified type
        """
        matching_strategies = []

        for strategy_id, strategy_class in self._strategies.items():
            if getattr(strategy_class, 'STRATEGY_TYPE', None) == strategy_type:
                matching_strategies.append(strategy_id)

        return matching_strategies

    def get_strategy_types(self) -> List[str]:
        """
        Get all available strategy types.

        Returns:
            List of strategy type names
        """
        types = set()
        for strategy_class in self._strategies.values():
            strategy_type = getattr(strategy_class, 'STRATEGY_TYPE', StrategyType.TREND_FOLLOWING)
            types.add(strategy_type.value)

        return sorted(list(types))


# Global registry instance
registry = StrategyRegistry()


def get_registry() -> StrategyRegistry:
    """Get the global strategy registry instance."""
    return registry