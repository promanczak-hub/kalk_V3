"""
Prosty TTL cache dla danych konfiguracyjnych (tabele referencyjne).
Eliminuje powtarzające się zapytania do Supabase dla danych które zmieniają się rzadko.
TTL = 300s (5 minut). Cache żyje w pamięci procesu FastAPI.
"""

import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SimpleCache:
    """Lekki, thread-safe (dla GIL) cache z TTL."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, ts = entry
        if time.monotonic() - ts > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
        logger.debug("Cache invalidated: %s", key)

    def clear(self) -> None:
        self._store.clear()
        logger.debug("Cache cleared")


# Singleton cache dla całej aplikacji — 5 minuut TTL
config_cache = SimpleCache(ttl_seconds=300)
