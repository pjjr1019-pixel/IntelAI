"""
cache.py — Caching utilities for API responses with Redis support.
"""

from __future__ import annotations

import asyncio
import json
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from vanguard_signal.config import settings


class CacheBackend:
    """Abstract cache backend interface."""

    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        raise NotImplementedError

    async def clear(self, pattern: Optional[str] = None) -> None:
        raise NotImplementedError


class MemoryCache(CacheBackend):
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


class RedisCache(CacheBackend):
    """Redis-based cache backend."""

    def __init__(self):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis package not available")

        self._redis = redis.Redis.from_url(settings.redis.url, decode_responses=True)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value from Redis."""
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            # If Redis fails, return None (fail gracefully)
            pass
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set cached value in Redis with TTL."""
        try:
            json_data = json.dumps(value)
            await self._redis.setex(key, ttl_seconds, json_data)
        except Exception:
            # If Redis fails, ignore (fail gracefully)
            pass

    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries matching pattern or all if no pattern."""
        try:
            if pattern:
                # Use SCAN to find keys matching pattern
                keys = []
                async for key in self._redis.scan_iter(pattern):
                    keys.append(key)
                if keys:
                    await self._redis.delete(*keys)
            else:
                await self._redis.flushdb()
        except Exception:
            # If Redis fails, ignore (fail gracefully)
            pass


class Cache:
    """Unified cache interface that automatically chooses backend."""

    def __init__(self):
        if settings.redis.enabled and REDIS_AVAILABLE:
            try:
                self._backend = RedisCache()
                self._backend_type = "redis"
            except Exception:
                # Fall back to memory cache if Redis fails
                self._backend = MemoryCache()
                self._backend_type = "memory"
        else:
            self._backend = MemoryCache()
            self._backend_type = "memory"

    async def get(self, key: str) -> Optional[Any]:
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._backend.set(key, value, ttl_seconds)

    async def clear(self, pattern: Optional[str] = None) -> None:
        await self._backend.clear(pattern)

    @property
    def backend_type(self) -> str:
        return self._backend_type


# Global cache instance
cache = Cache()


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
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


async def clear_cache(pattern: Optional[str] = None) -> None:
    """Clear cache entries. Use pattern to allow selective clearing."""
    await cache.clear(pattern)


# Create global cache instance
cache = Cache()