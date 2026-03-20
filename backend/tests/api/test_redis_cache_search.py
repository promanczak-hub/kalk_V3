# tests/api/test_redis_cache_search.py
"""Unit tests for Redis cache layer in scoring_search_routes.

All tests mock Redis and Supabase — no real connections required.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_redis_client():
    """Return a MagicMock pretending to be a Redis client."""
    client = MagicMock()
    client.get.return_value = None  # default: cache miss
    client.setex.return_value = True
    client.ping.return_value = True
    return client


@pytest.fixture()
def initial_data_payload() -> dict[str, Any]:
    return {
        "brands": ["Toyota", "BMW"],
        "models": [],
        "samar_class_ids": [],
    }


# ── cache_invalidate_pattern / get_cache_stats ────────────────────────────────


class TestCacheHelpers:
    def test_invalidate_pattern_deletes_keys(
        self, mock_redis_client: MagicMock
    ) -> None:
        """cache_invalidate_pattern removes all matching keys."""
        mock_redis_client.scan_iter.return_value = [
            "kalk_v3:search:abc",
            "kalk_v3:search:def",
        ]

        with patch("core.redis_cache._get_client", return_value=mock_redis_client):
            from core.redis_cache import cache_invalidate_pattern

            deleted = cache_invalidate_pattern("search:*")

        assert deleted == 2
        mock_redis_client.delete.assert_called_once()

    def test_invalidate_pattern_no_redis(self) -> None:
        """cache_invalidate_pattern returns 0 when Redis is unavailable."""
        with patch("core.redis_cache._get_client", return_value=None):
            from core.redis_cache import cache_invalidate_pattern

            assert cache_invalidate_pattern("search:*") == 0

    def test_get_cache_stats_connected(self, mock_redis_client: MagicMock) -> None:
        """get_cache_stats returns proper dict when Redis is available."""
        mock_redis_client.info.return_value = {"used_memory": 2 * 1024 * 1024}
        mock_redis_client.dbsize.return_value = 42

        with patch("core.redis_cache._get_client", return_value=mock_redis_client):
            from core.redis_cache import get_cache_stats

            stats = get_cache_stats()

        assert stats["available"] is True
        assert stats["key_count"] == 42
        assert stats["memory_mb"] == 2.0

    def test_get_cache_stats_unavailable(self) -> None:
        """get_cache_stats returns safe defaults when Redis is down."""
        with patch("core.redis_cache._get_client", return_value=None):
            from core.redis_cache import get_cache_stats

            stats = get_cache_stats()

        assert stats["available"] is False
        assert stats["key_count"] == 0
        assert stats["memory_mb"] == 0.0


# ── initial-data caching ──────────────────────────────────────────────────────


class TestInitialDataCache:
    def test_cache_hit_skips_rpc(self, mock_redis_client: MagicMock) -> None:
        """When Redis has cached data, the Supabase RPC is NOT called."""
        cached_payload = {
            "brands": ["Toyota"],
            "models": [],
            "brand_model_map": {"Toyota": []},
            "brand_counts": {},
            "samar_classes": [],
            "body_types": [],
        }
        mock_redis_client.get.return_value = json.dumps(cached_payload)

        with (
            patch("core.redis_cache._get_client", return_value=mock_redis_client),
            patch(
                "api.scoring_search_routes._get_client", return_value=mock_redis_client
            ),
            patch("api.scoring_search_routes.supabase") as mock_sb,
        ):
            from api.scoring_search_routes import get_initial_data

            result = get_initial_data()

        mock_sb.rpc.assert_not_called()
        assert result.brands == ["Toyota"]

    def test_cache_miss_calls_rpc_and_stores(
        self, mock_redis_client: MagicMock
    ) -> None:
        """On cache miss, RPC is called and the result is stored in Redis."""
        mock_redis_client.get.return_value = None
        rpc_data = {
            "brands": ["BMW"],
            "models": ["X3"],
            "brand_model_map": {"BMW": ["X3"]},
            "brand_counts": {"BMW": 1},
            "samar_classes": [{"id": 1}],
            "body_types": [],
        }

        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value.data = rpc_data

        with (
            patch("core.redis_cache._get_client", return_value=mock_redis_client),
            patch(
                "api.scoring_search_routes._get_client", return_value=mock_redis_client
            ),
            patch("api.scoring_search_routes.supabase", mock_sb),
        ):
            from api.scoring_search_routes import get_initial_data

            result = get_initial_data()

        mock_sb.rpc.assert_called_once_with("rpc_get_scoring_initial_data")
        mock_redis_client.setex.assert_called_once()
        assert result.brands == ["BMW"]


# ── search caching ────────────────────────────────────────────────────────────


class TestSearchCache:
    def _make_request(self) -> Any:
        from core.models_scoring_search import ScoringSearchRequest, ScoringRequirement

        return ScoringSearchRequest(
            brands=["Toyota"],
            models=[],
            samar_class_ids=[],
            requirements=[
                ScoringRequirement(
                    feature_key="monthly_price_net",
                    operator="lte",
                    value=5000,
                    requirement="MUST_HAVE",
                    weight=1,
                )
            ],
            offset=0,
            limit=20,
        )

    def test_different_requests_get_different_cache_keys(self) -> None:
        """Two distinct search payloads produce different MD5 hashes."""
        from api.scoring_search_routes import _params_hash

        hash1 = _params_hash('{"brands": ["Toyota"]}')
        hash2 = _params_hash('{"brands": ["BMW"]}')
        assert hash1 != hash2

    def test_redis_unavailable_fallthrough(self) -> None:
        """When Redis is down, search still works via direct Supabase call."""
        rpc_data = [
            {
                "vehicle_id": "abc",
                "brand": "Toyota",
                "model": "Yaris",
                "version": None,
                "match_score_pct": 100.0,
                "matched_features": ["monthly_price_net"],
                "missing_features": [],
                "best_monthly_price": 1500.0,
            }
        ]

        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value.data = rpc_data

        with (
            patch("core.redis_cache._get_client", return_value=None),
            patch("api.scoring_search_routes._get_client", return_value=None),
            patch("api.scoring_search_routes.supabase", mock_sb),
        ):
            from api.scoring_search_routes import run_scoring_search

            result = run_scoring_search(self._make_request())

        assert result.total_count == 1
        assert result.results[0].brand == "Toyota"
