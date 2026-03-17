"""Redis cache layer for LTR calculator DB lookups.

Provides a decorator ``redis_cache`` that stores function results in Redis
with configurable TTL.  Falls back to direct DB calls when Redis is
unavailable (connection refused, timeout, etc.) — the system never crashes
because of Redis being down.

Environment variable ``REDIS_URL`` controls the connection.
Default: ``redis://localhost:6379/0``
"""

import json
import logging
import os
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_PREFIX = "kalk_v3:"

# ── Lazy singleton Redis client ──
_client: Any = None
_redis_available: bool | None = None


def _get_client() -> Any:
    """Return a Redis client (lazy-init, singleton)."""
    global _client, _redis_available
    if _client is not None:
        return _client
    try:
        import redis as redis_lib

        _client = redis_lib.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _client.ping()
        _redis_available = True
        logger.info("Redis connected: %s", REDIS_URL)
    except Exception as exc:
        _redis_available = False
        _client = None
        logger.warning(
            "Redis niedostępny (%s). Fallback na lru_cache. Błąd: %s",
            REDIS_URL,
            exc,
        )
    return _client


def is_redis_available() -> bool:
    """Check if Redis is connected and responding."""
    global _redis_available
    if _redis_available is None:
        _get_client()
    return bool(_redis_available)


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
                f"{_PREFIX}{prefix}{func.__name__}:"
                f"{':'.join(str(a) for a in args)}"
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
