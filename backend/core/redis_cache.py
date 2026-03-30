"""Redis cache layer for LTR calculator DB lookups.

Provides:
- ``redis_cache`` decorator — stores function results in Redis with configurable
  TTL.  Falls back to direct DB calls when Redis is unavailable.
- ``cache_invalidate_pattern`` — bulk-delete keys by glob pattern.
- ``get_cache_stats`` — lightweight stats dict for health/diagnostics.

Environment variable ``REDIS_URL`` controls the connection.
Default: ``redis://localhost:6379/0``
"""

import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
_PREFIX = "kalk_v3:"

# ── Lazy singleton Redis client ──
_client: Any = None
_redis_available: bool | None = None
_redis_down_until: float = 0.0
_redis_backoff_seconds: float = 60.0


def _get_client() -> Any:
    """Return a Redis client (lazy-init, singleton)."""
    global _client, _redis_available, _redis_down_until
    if _client is not None:
        return _client
        
    if time.time() < _redis_down_until:
        return None
        
    try:
        import redis as redis_lib

        _client = redis_lib.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=1.0,
        )
        _client.ping()
        _redis_available = True
        logger.info("Redis connected: %s", REDIS_URL)
        return _client
    except Exception as exc:
        _redis_available = False
        _client = None
        _redis_down_until = time.time() + _redis_backoff_seconds
        logger.warning(
            "Redis niedostępny (%s). Circuit breaker otwarty na %ds. Fallback na funkcję. Błąd: %s",
            REDIS_URL,
            int(_redis_backoff_seconds),
            exc,
        )
        return None


def is_redis_available() -> bool:
    """Check if Redis is connected and responding."""
    global _redis_available, _redis_down_until
    if _client is None and time.time() >= _redis_down_until:
        _get_client()
    return bool(_redis_available)


def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all Redis keys matching *pattern* (glob).

    Returns the number of deleted keys. Returns 0 if Redis is unavailable.
    """
    client = _get_client()
    if client is None:
        return 0
    full_pattern = f"{_PREFIX}{pattern}"
    keys = list(client.scan_iter(match=full_pattern, count=500))
    if keys:
        client.delete(*keys)
    logger.debug("Invalidated %d Redis keys matching '%s'", len(keys), full_pattern)
    return len(keys)


def get_cache_stats() -> dict[str, Any]:
    """Return lightweight Redis statistics for health/diagnostics."""
    client = _get_client()
    if client is None:
        return {"available": False, "key_count": 0, "memory_mb": 0.0}
    try:
        info = client.info("memory")
        key_count = sum(
            client.dbsize()
            for _ in [None]  # dbsize across current DB
        )
        memory_bytes: int = info.get("used_memory", 0)
        return {
            "available": True,
            "key_count": key_count,
            "memory_mb": round(memory_bytes / (1024 * 1024), 2),
        }
    except Exception as exc:
        logger.debug("Redis stats error: %s", exc)
        return {"available": False, "key_count": 0, "memory_mb": 0.0}


def redis_cache(
    ttl_seconds: int = 3600,
    prefix: str = "",
) -> Callable:
    """Decorator: cache function result in Redis with JSON serialisation.

    Falls back to calling the function directly when Redis is down.
    Keys are built from ``prefix + function_name + str(args)``.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = _get_client()
            cache_key = (
                f"{_PREFIX}{prefix}{func.__name__}:{':'.join(str(a) for a in args)}"
            )

            # Try read from cache
            if client is not None:
                try:
                    cached = client.get(cache_key)
                    if cached is not None:
                        return json.loads(cached)
                except Exception as exc:
                    logger.debug("Redis GET error for %s: %s", cache_key, exc)

            # Cache miss — call original function
            result = func(*args, **kwargs)

            # Try write to cache
            if client is not None:
                try:
                    client.setex(
                        cache_key,
                        ttl_seconds,
                        json.dumps(result, default=str),
                    )
                except Exception as exc:
                    logger.debug("Redis SET error for %s: %s", cache_key, exc)

            return result

        # Expose cache_clear for testing / manual invalidation
        def cache_clear() -> int:
            """Delete all keys matching this function's prefix."""
            client = _get_client()
            if client is None:
                return 0
            pattern = f"{_PREFIX}{prefix}{func.__name__}:*"
            keys = list(client.scan_iter(match=pattern, count=500))
            if keys:
                client.delete(*keys)
            return len(keys)

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
