"""Tests for LLM-based feature enrichment matching.

Uses pytest-mock to isolate LLM and DB calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from core.feature_enrichment import (
    _CONFIDENCE_THRESHOLD,
    _llm_match_equipment,
    _normalize_body_style,
    enrich_vehicle_features,
)

import pytest

# ── Fixtures ───────────────────────────────────────────────────────────────


SAMPLE_FEATURES: list[dict[str, Any]] = [
    {
        "id": "uuid-1",
        "feature_key": "felga_aluminiowa",
        "display_name": "felga aluminiowa",
        "feature_type": "boolean",
    },
    {
        "id": "uuid-2",
        "feature_key": "hak_holowniczy",
        "display_name": "Hak holowniczy/zaczep",
        "feature_type": "enum",
    },
    {
        "id": "uuid-3",
        "feature_key": "klimatyzacja_automatyczna",
        "display_name": "Klimatyzacja automatyczna",
        "feature_type": "boolean",
    },
]

LLM_SPARE_WHEEL_RESPONSE = {
    "matches": [
        {
            "item": "felga aluminiowa",
            "feature_key": "felga_aluminiowa",
            "confidence": 0.95,
        },
        {
            "item": "Koło zapasowe z felgą aluminiową",
            "feature_key": "",
            "confidence": 0.0,
        },
    ]
}

LLM_HIGH_CONFIDENCE_RESPONSE = {
    "matches": [
        {
            "item": "Klimatyzacja automatyczna",
            "feature_key": "klimatyzacja_automatyczna",
            "confidence": 0.92,
        },
        {"item": "nieznana opcja xyz", "feature_key": "", "confidence": 0.1},
    ]
}


# ── Helpers ────────────────────────────────────────────────────────────────


def _mock_gemini_response(payload: dict[str, Any]) -> MagicMock:
    """Build a mock Gemini response object with .parsed set to matched models."""
    from pydantic import BaseModel

    class MockMatchItem(BaseModel):
        item: str
        feature_key: str
        confidence: float

    class MockMatchesSchema(BaseModel):
        matches: list[MockMatchItem]

    mock_resp = MagicMock()
    matches = [MockMatchItem(**m) for m in payload.get("matches", [])]
    mock_resp.parsed = MockMatchesSchema(matches=matches)
    return mock_resp


# ── _llm_match_equipment ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_match_returns_only_high_confidence() -> None:
    """Items below the confidence threshold must be filtered out."""
    from unittest.mock import AsyncMock

    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        mock_client.return_value.aio.models.generate_content = AsyncMock(
            return_value=_mock_gemini_response(LLM_HIGH_CONFIDENCE_RESPONSE)
        )
        items = ["Klimatyzacja automatyczna", "nieznana opcja xyz"]
        results = await _llm_match_equipment(items, SAMPLE_FEATURES)

    assert len(results) == 1
    assert results[0]["feature_key"] == "klimatyzacja_automatyczna"
    assert results[0]["confidence"] >= _CONFIDENCE_THRESHOLD


@pytest.mark.asyncio
async def test_spare_wheel_not_matched_as_alloy_rim() -> None:
    """Regression: 'Koło zapasowe z felgą aluminiową' must NOT match 'felga_aluminiowa'."""
    from unittest.mock import AsyncMock

    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        mock_client.return_value.aio.models.generate_content = AsyncMock(
            return_value=_mock_gemini_response(LLM_SPARE_WHEEL_RESPONSE)
        )
        items = ["felga aluminiowa", "Koło zapasowe z felgą aluminiową"]
        results = await _llm_match_equipment(items, SAMPLE_FEATURES)

    matched_keys = [r["feature_key"] for r in results]
    assert "felga_aluminiowa" in matched_keys, "alloy rim should still match"
    # Spare wheel must not be matched to the alloy rim feature
    assert len(results) == 1, "spare wheel must produce no match"


@pytest.mark.asyncio
async def test_llm_match_fallback_on_error() -> None:
    """LLM error must propagate (Fail Fast) when Gemini raises.

    `_llm_match_equipment` checks `_get_aliases()` first — if the alias for
    'felga aluminiowa' is cached in DB, the function early-returns BEFORE
    Gemini is invoked, and the RuntimeError never fires. Patching _get_aliases
    to return {} forces the LLM path so we can verify the exception propagates.
    Without this patch the test was flaky depending on Supabase aliases cache state.
    """
    from unittest.mock import AsyncMock

    with (
        patch("core.feature_enrichment._get_aliases", AsyncMock(return_value={})),
        patch("core.feature_enrichment.get_gemini_client") as mock_client,
    ):
        mock_client.return_value.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("quota exceeded")
        )
        # Production wraps the raw exception in a Polish-language RuntimeError:
        # "Zatrzymano proces enrichment - błąd komunikacji z LLM." (from chain `from exc`).
        with pytest.raises(RuntimeError, match="Zatrzymano proces enrichment"):
            await _llm_match_equipment(["felga aluminiowa"], SAMPLE_FEATURES)


@pytest.mark.asyncio
async def test_llm_match_empty_inputs() -> None:
    """Empty items or features list returns empty without calling LLM."""
    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        assert await _llm_match_equipment([], SAMPLE_FEATURES) == []
        assert await _llm_match_equipment(["felga aluminiowa"], []) == []
        mock_client.assert_not_called()


# ── enrich_vehicle_features ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrich_vehicle_features_uses_llm_for_equipment() -> None:
    """End-to-end: enrich calls _llm_match_equipment for std_equipment."""
    synthesis_data = {
        "card_summary": {
            "standard_equipment": ["felga aluminiowa"],
            "paid_options": [],
        }
    }
    from unittest.mock import AsyncMock

    with (
        patch(
            "core.feature_enrichment._load_feature_catalog",
            return_value=SAMPLE_FEATURES,
        ),
        patch(
            "core.feature_enrichment._llm_match_equipment",
            AsyncMock(
                return_value=[
                    {
                        "item": "felga aluminiowa",
                        "feature_key": "felga_aluminiowa",
                        "confidence": 0.95,
                    }
                ]
            ),
        ),
        patch("core.feature_enrichment.sb_client") as mock_sb,
        patch(
            "core.feature_enrichment.resolve_vehicle_features",
            return_value={"resolved": 1},
        ),
    ):
        mock_sb.schema.return_value.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        result = await enrich_vehicle_features("vehicle-uuid", synthesis_data)

        assert result["evidence_created"] == 1
        assert result["errors"] == []


@pytest.mark.asyncio
async def test_enrich_returns_error_on_missing_card_summary() -> None:
    """Missing card_summary must return an error dict, not crash."""
    result = await enrich_vehicle_features("vehicle-uuid", {})
    assert "error" in result
    assert result["evidence_created"] == 0


# ── _normalize_body_style ──────────────────────────────────────────────────────


def test_normalize_body_style_sportstourer() -> None:
    """Sportstourer and its variants must map to Kombi."""
    assert _normalize_body_style("Sportstourer") == "Kombi"
    assert _normalize_body_style("SPORTSTOURER") == "Kombi"
    assert _normalize_body_style("Sports Tourer") == "Kombi"
    assert _normalize_body_style("SPORTS TOURER") == "Kombi"


def test_normalize_body_style_kombi_aliases() -> None:
    """All Kombi aliases must resolve correctly."""
    for alias in [
        "Touring",
        "Avant",
        "Wagon",
        "Estate",
        "Variant",
        "Sportswagon",
        "Break",
        "SW",
        "Alltrack",
    ]:
        assert _normalize_body_style(alias) == "Kombi", (
            f"Expected Kombi for alias '{alias}'"
        )


def test_normalize_body_style_suv_aliases() -> None:
    """SUV aliases must resolve to SUV."""
    assert _normalize_body_style("Crossover") == "SUV"
    assert _normalize_body_style("CROSS") == "SUV"


def test_normalize_body_style_passthrough_canonical() -> None:
    """Canonical names must pass through unchanged (correct casing)."""
    assert _normalize_body_style("SUV") == "SUV"
    assert _normalize_body_style("Van") == "Van"
    assert _normalize_body_style("Hatchback") == "Hatchback"
    assert _normalize_body_style("Sedan") == "Sedan"
    assert _normalize_body_style("Kombi") == "Kombi"


def test_normalize_body_style_unknown_survives() -> None:
    """Completely unknown value must not crash — returns title-cased string."""
    result = _normalize_body_style("CoolCar2000")
    assert isinstance(result, str)
    assert len(result) > 0


def test_normalize_body_style_empty_string() -> None:
    """Empty / whitespace input returns input unchanged."""
    assert _normalize_body_style("") == ""
    assert _normalize_body_style("  ") == "  "
