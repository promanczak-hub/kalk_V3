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
    """Build a mock Gemini response object with .text set to JSON."""
    import json

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(payload)
    return mock_resp


# ── _llm_match_equipment ──────────────────────────────────────────────────


def test_llm_match_returns_only_high_confidence() -> None:
    """Items below the confidence threshold must be filtered out."""
    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = (
            _mock_gemini_response(LLM_HIGH_CONFIDENCE_RESPONSE)
        )
        items = ["Klimatyzacja automatyczna", "nieznana opcja xyz"]
        results = _llm_match_equipment(items, SAMPLE_FEATURES)

    assert len(results) == 1
    assert results[0]["feature_key"] == "klimatyzacja_automatyczna"
    assert results[0]["confidence"] >= _CONFIDENCE_THRESHOLD


def test_spare_wheel_not_matched_as_alloy_rim() -> None:
    """Regression: 'Koło zapasowe z felgą aluminiową' must NOT match 'felga_aluminiowa'."""
    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = (
            _mock_gemini_response(LLM_SPARE_WHEEL_RESPONSE)
        )
        items = ["felga aluminiowa", "Koło zapasowe z felgą aluminiową"]
        results = _llm_match_equipment(items, SAMPLE_FEATURES)

    matched_keys = [r["feature_key"] for r in results]
    assert "felga_aluminiowa" in matched_keys, "alloy rim should still match"
    # Spare wheel must not be matched to the alloy rim feature
    assert len(results) == 1, "spare wheel must produce no match"


def test_llm_match_fallback_on_error() -> None:
    """LLM error must return empty list, not raise an exception."""
    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        mock_client.return_value.models.generate_content.side_effect = RuntimeError(
            "quota exceeded"
        )
        results = _llm_match_equipment(["felga aluminiowa"], SAMPLE_FEATURES)

    assert results == []


def test_llm_match_empty_inputs() -> None:
    """Empty items or features list returns empty without calling LLM."""
    with patch("core.feature_enrichment.get_gemini_client") as mock_client:
        assert _llm_match_equipment([], SAMPLE_FEATURES) == []
        assert _llm_match_equipment(["felga aluminiowa"], []) == []
        mock_client.assert_not_called()


# ── enrich_vehicle_features ───────────────────────────────────────────────


def test_enrich_vehicle_features_uses_llm_for_equipment(mocker: Any) -> None:
    """End-to-end: enrich calls _llm_match_equipment for std_equipment."""
    synthesis_data = {
        "card_summary": {
            "standard_equipment": ["felga aluminiowa"],
            "paid_options": [],
        }
    }
    mocker.patch(
        "core.feature_enrichment._load_feature_catalog",
        return_value=SAMPLE_FEATURES,
    )
    mocker.patch(
        "core.feature_enrichment._llm_match_equipment",
        return_value=[
            {
                "item": "felga aluminiowa",
                "feature_key": "felga_aluminiowa",
                "confidence": 0.95,
            }
        ],
    )
    mock_sb = mocker.patch("core.feature_enrichment.sb_client")
    mock_sb.schema.return_value.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    mocker.patch(
        "core.feature_enrichment.resolve_vehicle_features",
        return_value={"resolved": 1},
    )

    result = enrich_vehicle_features("vehicle-uuid", synthesis_data)

    assert result["evidence_created"] == 1
    assert result["errors"] == []


def test_enrich_returns_error_on_missing_card_summary() -> None:
    """Missing card_summary must return an error dict, not crash."""
    result = enrich_vehicle_features("vehicle-uuid", {})
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
    for alias in ["Touring", "Avant", "Wagon", "Estate", "Variant", "Sportswagon", "Break", "SW", "Alltrack"]:
        assert _normalize_body_style(alias) == "Kombi", f"Expected Kombi for alias '{alias}'"


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
