"""
Cache Module

Provides a unified caching abstraction that supports:
- In-memory cache with TTL (default/fallback)
- Redis cache for distributed deployments

Usage:
    from forex.cache import get_cache_backend
    cache = get_cache_backend()
    cache.set("key", value, ttl_seconds=300)
    value = cache.get("key")
"""

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get a value from the cache. Returns None if not found or expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set a value in the cache with TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass


class InMemoryCache(CacheBackend):
    """
    Thread-safe in-memory cache with TTL support.

    This is the default/fallback cache for local development
    and single-instance deployments.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, datetime] = {}
        self._ttls: dict[str, int] = {}
        self._lock = threading.RLock()

    def _is_valid(self, key: str) -> bool:
        """Check if a cache entry is still valid."""
        if key not in self._timestamps:
            return False
        cache_time = self._timestamps[key]
        ttl = self._ttls.get(key, 300)
        return (datetime.now() - cache_time).total_seconds() < ttl

    def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        with self._lock:
            if key in self._cache and self._is_valid(key):
                return self._cache[key]
            # Clean up expired entry
            if key in self._cache:
                del self._cache[key]
                self._timestamps.pop(key, None)
                self._ttls.pop(key, None)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set a value in the cache."""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
            self._ttls[key] = ttl_seconds

    def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            self._ttls.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._ttls.clear()


class RedisCache(CacheBackend):
    """
    Redis-based cache for distributed deployments.

    Enables horizontal scaling by sharing cache state across
    multiple application instances.

    Environment Variables:
        REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    """

    def __init__(self, redis_url: str | None = None) -> None:
        try:
            import redis
        except ImportError as e:
            raise ImportError("Redis package not installed. Install with: pip install redis") from e

        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._client = redis.from_url(url, decode_responses=True)
        self._prefix = "forex:"

        # Test connection
        try:
            self._client.ping()
            logger.info(f"Connected to Redis at {url}")
        except redis.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}") from e

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Any | None:
        """Get a value from Redis."""
        try:
            data = self._client.get(self._make_key(key))
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis GET error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set a value in Redis with TTL."""
        try:
            data = json.dumps(value, default=str)
            self._client.setex(self._make_key(key), ttl_seconds, data)
        except Exception as e:
            logger.warning(f"Redis SET error for {key}: {e}")

    def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        try:
            self._client.delete(self._make_key(key))
        except Exception as e:
            logger.warning(f"Redis DELETE error for {key}: {e}")

    def clear(self) -> None:
        """Clear all forex-related cached values."""
        try:
            keys = self._client.keys(f"{self._prefix}*")
            if keys:
                self._client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis CLEAR error: {e}")


# Singleton cache instance
_cache_instance: CacheBackend | None = None


def get_cache_backend(force_backend: str | None = None) -> CacheBackend:
    """
    Factory function to get the appropriate cache backend.

    Priority:
    1. force_backend parameter ("redis" or "memory")
    2. CACHE_BACKEND environment variable
    3. Auto-detect: Try Redis, fallback to in-memory

    Args:
        force_backend: Force a specific backend ("redis" or "memory")

    Returns:
        CacheBackend instance
    """
    global _cache_instance

    if _cache_instance is not None and force_backend is None:
        return _cache_instance

    backend = force_backend or os.environ.get("CACHE_BACKEND", "auto")

    if backend == "memory":
        logger.info("Using in-memory cache (explicitly configured)")
        _cache_instance = InMemoryCache()
    elif backend == "redis":
        _cache_instance = RedisCache()
    else:
        # Auto-detect: try Redis, fallback to memory
        try:
            _cache_instance = RedisCache()
        except (ImportError, ConnectionError) as e:
            logger.info(f"Redis not available ({e}), using in-memory cache")
            _cache_instance = InMemoryCache()

    return _cache_instance


def reset_cache_backend() -> None:
    """Reset the cache singleton. Useful for testing."""
    global _cache_instance
    if _cache_instance is not None:
        _cache_instance.clear()
    _cache_instance = None
