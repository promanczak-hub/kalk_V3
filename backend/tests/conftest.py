"""Pytest conftest — shared fixtures + autouse cache reset.

Why an autouse cache reset:
- Multiple modules in `core/` use `@lru_cache` decorators (e.g.
  `LTRSubCalculatorSerwisNew.get_service_multiplier`, `get_base_service_rate`,
  `get_all_service_rates`; `feature_cross_reference._load_feature_catalog`;
  `ltr_db_fetchers.*`; `ltr_vehicle_resolvers.*`).
- Other modules in `core/` use `@redis_cache` (samar_rv_fetchers, samar_rv).
- When earlier tests in the suite (e.g. test_feature_enrichment) populate
  these caches with values derived from mocked DB state, the cached entries
  leak into later tests that expect fresh DB queries — producing order-
  dependent failures (Skoda parity drifts ~1664 PLN brutto in full suite).

This autouse fixture clears all such caches BEFORE each test starts, making
the suite order-independent. It's belt-and-suspenders with per-test
`monkeypatch.setattr("core.redis_cache._get_client", lambda: None)` calls
in parity tests.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

import pytest

logger = logging.getLogger(__name__)


# ── Modules with @lru_cache to clear between tests ────────────────────────
_LRU_CACHED_MODULES: list[str] = [
    "core.LTRSubCalculatorSerwisNew",
    "core.feature_cross_reference",
    "core.feature_catalog_loader",
    "core.ltr_db_fetchers",
    "core.ltr_vehicle_resolvers",
    "core.samar_rv",  # decorator imports may include lru_cache wrappers
]


def _clear_lru_caches_in_module(module_name: str) -> None:
    """Find and call .cache_clear() on every @lru_cache decorated function in a module."""
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        logger.debug("Could not import %s for cache clear: %s", module_name, exc)
        return
    for attr_name in dir(module):
        attr = getattr(module, attr_name, None)
        if attr is None:
            continue
        cache_clear = getattr(attr, "cache_clear", None)
        if callable(cache_clear):
            try:
                cache_clear()
            except Exception as exc:
                logger.debug(
                    "cache_clear failed for %s.%s: %s", module_name, attr_name, exc
                )


def _reset_redis_singleton() -> None:
    """Reset the lazy Redis singleton in core.redis_cache so the next call re-checks."""
    try:
        import core.redis_cache as rc_module

        rc_module._client = None
        rc_module._redis_available = None
        rc_module._redis_down_until = 0.0
    except Exception as exc:
        logger.debug("Could not reset redis_cache singleton: %s", exc)


_supabase_reset_counter = 0


def _maybe_refresh_supabase_singleton() -> None:
    """Recreate the global Supabase client every N tests to flush exhausted HTTP/2 connections.

    The supabase singleton in `core.database` holds a long-lived HTTP/2 connection.
    Under Windows test load (~500 tests/run), Supabase / the local TCP stack
    exhausts ephemeral ports → `httpx.ConnectError: [WinError 10061]` cascade,
    causing fetcher tests (Skoda parity, golden path, pipeline_debugger) to fail.

    Refreshing the client every 25 tests rotates the HTTP connection pool and
    yields fresh ephemeral ports, eliminating the cascade. Cheap: create_client
    is ~50ms; the saving is making a previously-flaky suite deterministic.
    """
    global _supabase_reset_counter
    _supabase_reset_counter += 1
    if _supabase_reset_counter % 25 != 1:  # refresh on test #1, #26, #51, ...
        return
    try:
        import core.database as db_module
        from supabase import create_client

        db_module.supabase = create_client(
            db_module.SUPABASE_URL,
            db_module.SUPABASE_KEY,
            options=db_module.options,
        )
        db_module._supabase_admin = None
    except Exception as exc:
        logger.debug("Could not refresh supabase singleton: %s", exc)


@pytest.fixture(autouse=True)
def _reset_caches_between_tests() -> Any:
    """Autouse — clear lru_caches + redis singleton before every test.

    This prevents cross-test pollution of cached DB lookups (samar_rv,
    service multipliers, feature catalog, etc.) that caused order-dependent
    failures in the full suite (Skoda parity, pipeline_debugger).
    """
    for module_name in _LRU_CACHED_MODULES:
        _clear_lru_caches_in_module(module_name)
    _reset_redis_singleton()
    _maybe_refresh_supabase_singleton()
    yield
    # Post-test cleanup is implicit via the next test's pre-yield reset.
