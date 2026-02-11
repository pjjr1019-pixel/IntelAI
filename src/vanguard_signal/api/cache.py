"""
cache.py — Simple caching utilities for API responses.
"""

from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional


class SimpleCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry['expires']:
                    return entry['value']
                else:
                    # Expired, remove it
                    del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set cached value with TTL."""
        async with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': time.time() + ttl_seconds
            }

    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries matching pattern or all if no pattern."""
        async with self._lock:
            if pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
            else:
                self._cache.clear()


# Global cache instance
_cache = SimpleCache()


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator to cache async function results.

    Args:
        ttl_seconds: Time to live in seconds (default 5 minutes)
        key_prefix: Prefix for cache keys to allow selective clearing
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = "|".join(key_parts)

            # Try to get from cache
            cached_result = await _cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await _cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


async def clear_cache(pattern: Optional[str] = None) -> None:
    """Clear cache entries. Use pattern to clear specific entries."""
    await _cache.clear(pattern)