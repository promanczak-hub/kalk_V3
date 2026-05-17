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

    def test_cache_miss_calls_db_and_stores(
        self, mock_redis_client: MagicMock
    ) -> None:
        """On cache miss, DB is queried (vehicle_synthesis + samar_classes) and result is stored in Redis.

        Previously this tested an rpc() call (`rpc_get_scoring_initial_data`) but
        get_initial_data was rewritten to aggregate in Python from vehicle_synthesis
        rows. Cache contract is the same: miss → fetch → setex.
        """
        mock_redis_client.get.return_value = None  # cache miss

        # _supabase_execute_with_retry is called twice in get_initial_data:
        # 1) fetch vehicle_synthesis rows  2) fetch samar_classes
        synthesis_resp = MagicMock(
            data=[
                {
                    "brand": "BMW",
                    "model": "X3",
                    "synthesis_data": {
                        "card_summary": {"trim_level": "M Sport"},
                        "mapped_ai_data": {"body_style": "SUV"},
                    },
                }
            ]
        )
        samar_resp = MagicMock(data=[{"id": 1, "name": "Klasa 10"}])

        with (
            patch("core.redis_cache._get_client", return_value=mock_redis_client),
            patch(
                "api.scoring_search_routes._get_client", return_value=mock_redis_client
            ),
            patch(
                "api.scoring_search_routes._supabase_execute_with_retry",
                side_effect=[synthesis_resp, samar_resp],
            ),
        ):
            from api.scoring_search_routes import get_initial_data

            result = get_initial_data()

        # Verify cache write happened
        mock_redis_client.setex.assert_called_once()
        # Verify aggregated result matches mocked input
        assert "BMW" in result.brands
        assert "X3" in result.models
        assert result.samar_classes[0]["name"] == "Klasa 10"


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
        """When Redis is down, search still works via plain SELECT from vehicle_synthesis.

        Previously this tested an rpc() call (`rpc_reverse_search`) but run_scoring_search
        was rewritten to use a plain SELECT on vehicle_synthesis (non-semantic path) +
        rpc_search_vehicles_multi_vector (semantic path with embeddings). Cache contract
        is the same: redis=None → DB path executes → result returned.
        """
        # Plain SELECT path returns vehicle_synthesis rows that get processed in-Python.
        # Mock one Toyota Yaris row that matches the test request (brands=["Toyota"]).
        synthesis_resp = MagicMock(
            data=[
                {
                    "id": "abc",
                    "brand": "Toyota",
                    "model": "Yaris",
                    "synthesis_data": {
                        "card_summary": {
                            "trim_level": None,
                            "base_price": 50000,
                            "power_hp": 90,
                        },
                        "mapped_ai_data": {},
                    },
                }
            ]
        )

        with (
            patch("core.redis_cache._get_client", return_value=None),
            patch("api.scoring_search_routes._get_client", return_value=None),
            patch(
                "api.scoring_search_routes._supabase_execute_with_retry",
                return_value=synthesis_resp,
            ),
        ):
            from api.scoring_search_routes import run_scoring_search

            result = run_scoring_search(self._make_request())

        # Even without Redis, the search path should produce a result for the mocked
        # Toyota Yaris row (which matches brand="Toyota" hard-filter from _make_request).
        assert result.total_count >= 1
        assert result.results[0].brand == "Toyota"
        assert result.results[0].model == "Yaris"
