"""Tests for cross-reference modules.

Covers deterministic functions (no mocks needed) and
orchestrator paths (mocked DB + LLM).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


from core.cross_ref_evidence import _classify_dimension
from core.cross_ref_llm import find_exact_variant_match
from core.cross_ref_models import CrossRefLLMError, VariantMatchResult


# ── Fixtures ───────────────────────────────────────────────────


def _make_variant(
    name: str,
    price_net: float | None = None,
    price_gross: float | None = None,
) -> dict[str, Any]:
    return {
        "variant_name": name,
        "price_net": price_net,
        "price_gross": price_gross,
    }


def _make_spec(
    base_price: float = 50000.0,
    trim_level: str = "",
    power_hp: int | None = None,
) -> dict[str, Any]:
    return {
        "base_price": base_price,
        "trim_level": trim_level,
        "power_hp": power_hp,
    }


# ══════════════════════════════════════════════════════════════
# find_exact_variant_match (deterministic, no mocks)
# ══════════════════════════════════════════════════════════════


class TestFindExactVariantMatch:
    """Tests for deterministic price-based variant matching."""

    def test_match_by_price_net(self) -> None:
        """Exact net price match returns the variant."""
        variants = [_make_variant("A", price_net=50000.0)]
        spec = _make_spec(base_price=50000.0)
        result = find_exact_variant_match(spec, variants)
        assert result is not None
        assert result["variant_name"] == "A"

    def test_match_by_price_gross_fallback(self) -> None:
        """Falls back to gross price when net doesn't match."""
        variants = [
            _make_variant("B", price_net=60000.0, price_gross=50000.0)
        ]
        spec = _make_spec(base_price=50000.0)
        result = find_exact_variant_match(spec, variants)
        assert result is not None
        assert result["variant_name"] == "B"

    def test_prefers_trim_match_over_plain_price(self) -> None:
        """Variant with trim_level in name beats plain price match."""
        variants = [
            _make_variant("Basic 100KM", price_net=50000.0),
            _make_variant("Comfort 150KM", price_net=50000.0),
        ]
        spec = _make_spec(
            base_price=50000.0, trim_level="Comfort"
        )
        result = find_exact_variant_match(spec, variants)
        assert result is not None
        assert result["variant_name"] == "Comfort 150KM"

    def test_no_match_when_price_differs(self) -> None:
        """No variant matches when price differs by > 1 PLN."""
        variants = [_make_variant("X", price_net=55000.0)]
        spec = _make_spec(base_price=50000.0)
        result = find_exact_variant_match(spec, variants)
        assert result is None

    def test_base_price_zero_returns_none(self) -> None:
        """Zero base price cannot match anything."""
        variants = [_make_variant("A", price_net=0.0)]
        spec = _make_spec(base_price=0.0)
        result = find_exact_variant_match(spec, variants)
        assert result is None

    def test_unparsable_price_skipped_gracefully(self) -> None:
        """Variant with 'N/A' price is skipped, not crashed."""
        variants = [
            {"variant_name": "Bad", "price_net": "N/A", "price_gross": None}
        ]
        spec = _make_spec(base_price=50000.0)
        result = find_exact_variant_match(spec, variants)
        assert result is None


# ══════════════════════════════════════════════════════════════
# _classify_dimension (deterministic, no mocks)
# ══════════════════════════════════════════════════════════════


class TestClassifyDimension:
    """Tests for dimension key classification."""

    def test_polish_cargo_length(self) -> None:
        result = _classify_dimension(
            "długość_przestrzeni_ładunkowej_w_mm"
        )
        assert result is not None
        dim, is_overall = result
        assert dim == "length_mm"
        assert is_overall is False

    def test_english_overall_width(self) -> None:
        result = _classify_dimension("overall_width")
        assert result is not None
        dim, is_overall = result
        assert dim == "width_mm"
        assert is_overall is True

    def test_unknown_key_returns_none(self) -> None:
        result = _classify_dimension("masa_wlasna_kg")
        assert result is None


# ══════════════════════════════════════════════════════════════
# create_evidence_batch (mocked DB)
# ══════════════════════════════════════════════════════════════


class TestCreateEvidenceBatch:
    """Tests for batch evidence creation."""

    def test_single_upsert_call_for_batch(self) -> None:
        """Batch upsert calls DB exactly once, not N times."""
        from core.cross_ref_models import MatchedFeature

        match_result = VariantMatchResult(
            matched_variant_name="Test Variant",
            confidence=0.95,
            reasoning="Test",
            features=[
                MatchedFeature(
                    feature_key="f1",
                    mapping_confidence=0.95,
                    value_bool=True,
                ),
                MatchedFeature(
                    feature_key="f2",
                    mapping_confidence=0.95,
                    value_num=1500.0,
                    unit="mm",
                ),
                MatchedFeature(
                    feature_key="low_conf",
                    mapping_confidence=0.50,  # below threshold
                    value_bool=True,
                ),
            ],
        )
        feature_id_map = {"f1": "uuid-1", "f2": "uuid-2"}

        with patch("core.cross_ref_evidence.sb_client") as mock_sb:
            mock_chain = (
                mock_sb.schema.return_value
                .table.return_value
                .upsert.return_value
                .execute
            )
            mock_chain.return_value = MagicMock()

            from core.cross_ref_evidence import create_evidence_batch

            count = create_evidence_batch(
                "vehicle-1", match_result, feature_id_map
            )

        assert count == 2  # 2 valid, 1 below threshold
        # Verify upsert called exactly ONCE (batch, not N+1)
        assert (
            mock_sb.schema.return_value
            .table.return_value
            .upsert.call_count == 1
        )


# ══════════════════════════════════════════════════════════════
# cross_reference_vehicle (orchestrator, mocked)
# ══════════════════════════════════════════════════════════════


class TestCrossReferenceVehicle:
    """Integration tests for the orchestrator."""

    def _mock_vehicle_response(self) -> MagicMock:
        resp = MagicMock()
        resp.data = [
            {
                "id": "v1",
                "synthesis_data": {
                    "card_summary": {
                        "brand": "VW",
                        "model": "Caddy",
                        "base_price": 50000,
                    }
                },
            }
        ]
        return resp

    def _mock_catalog_response(self) -> MagicMock:
        resp = MagicMock()
        resp.data = [
            {
                "id": "cat1",
                "display_name": "VW Caddy 2025",
                "extracted_data": {
                    "variants": [
                        {
                            "variant_name": "Caddy 2.0 TDI",
                            "price_net": 45000,
                        }
                    ]
                },
            }
        ]
        return resp

    @patch("core.feature_cross_reference.resolve_vehicle_features")
    @patch("core.feature_cross_reference.save_catalog_match")
    @patch("core.feature_cross_reference.create_body_param_evidence")
    @patch("core.feature_cross_reference.create_evidence_batch")
    @patch("core.feature_cross_reference.match_variant_with_llm")
    @patch("core.feature_cross_reference.find_exact_variant_match")
    @patch("core.feature_cross_reference._load_feature_catalog")
    @patch("core.feature_cross_reference.sb_client")
    def test_happy_path(
        self,
        mock_sb: MagicMock,
        mock_catalog: MagicMock,
        mock_exact: MagicMock,
        mock_llm: MagicMock,
        mock_evidence: MagicMock,
        mock_body: MagicMock,
        mock_audit: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        """LLM returns match with confidence 0.85."""
        mock_sb.table.return_value.select.return_value \
            .eq.return_value.limit.return_value \
            .execute.return_value = self._mock_vehicle_response()
        mock_sb.schema.return_value.table.return_value \
            .select.return_value.eq.return_value \
            .eq.return_value.limit.return_value \
            .execute.return_value = self._mock_catalog_response()

        mock_catalog.return_value = (
            ("f1",),
            (("f1", "uuid-1"),),
        )
        mock_exact.return_value = None
        mock_llm.return_value = VariantMatchResult(
            matched_variant_name="Caddy 2.0 TDI",
            confidence=0.85,
            reasoning="Good match",
        )
        mock_evidence.return_value = 5
        mock_body.return_value = 2
        mock_resolve.return_value = {"resolved": 7}

        from core.feature_cross_reference import (
            cross_reference_vehicle,
        )

        result = cross_reference_vehicle("v1", ["cat1"])

        assert result["status"] == "matched"
        assert result["confidence"] == 0.85

    @patch("core.feature_cross_reference._load_feature_catalog")
    @patch("core.feature_cross_reference.match_variant_with_llm")
    @patch("core.feature_cross_reference.find_exact_variant_match")
    @patch("core.feature_cross_reference.sb_client")
    def test_llm_error_returns_error_status(
        self,
        mock_sb: MagicMock,
        mock_exact: MagicMock,
        mock_llm: MagicMock,
        mock_catalog: MagicMock,
    ) -> None:
        """LLM infrastructure failure returns error, not no_match."""
        mock_sb.table.return_value.select.return_value \
            .eq.return_value.limit.return_value \
            .execute.return_value = self._mock_vehicle_response()
        mock_sb.schema.return_value.table.return_value \
            .select.return_value.eq.return_value \
            .eq.return_value.limit.return_value \
            .execute.return_value = self._mock_catalog_response()

        mock_catalog.return_value = (("f1",), (("f1", "uuid-1"),))
        mock_exact.return_value = None
        mock_llm.side_effect = CrossRefLLMError("API quota exceeded")

        from core.feature_cross_reference import (
            cross_reference_vehicle,
        )

        result = cross_reference_vehicle("v1", ["cat1"])

        assert result["status"] == "error"
        assert "LLM" in result["message"]
