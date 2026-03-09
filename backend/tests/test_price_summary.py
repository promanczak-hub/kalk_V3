"""Tests for core.pipeline_price_summary — LLM price summary generation."""

from unittest.mock import MagicMock, patch

from core.pipeline_price_summary import (
    _deterministic_fallback,
    _deterministic_high,
    generate_price_summary,
)


class TestDeterministicHigh:
    """No warnings → HIGH confidence static summary."""

    def test_returns_high_confidence(self) -> None:
        result = _deterministic_high()
        assert result["confidence"] == "HIGH"
        assert "spójne" in result["verdict"].lower()
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) == 0


class TestDeterministicFallback:
    """Template-based fallback when LLM is unavailable."""

    def test_swap_detected(self) -> None:
        warnings = [
            {"rule": "BASE_TOTAL_SWAPPED", "severity": "ERROR", "message": "..."},
        ]
        result = _deterministic_fallback(warnings)
        assert result["confidence"] == "LOW"
        assert "zamian" in result["verdict"].lower()
        assert len(result["suggestions"]) > 0

    def test_generic_error(self) -> None:
        warnings = [
            {
                "rule": "BASE_PLUS_OPTIONS_VS_TOTAL",
                "severity": "ERROR",
                "message": "...",
            },
        ]
        result = _deterministic_fallback(warnings)
        assert result["confidence"] == "LOW"
        assert "1" in result["verdict"]  # "1 poważnych problemów"

    def test_warning_only_medium(self) -> None:
        warnings = [
            {
                "rule": "OPTION_PRICE_UNPARSEABLE",
                "severity": "WARNING",
                "message": "...",
            },
        ]
        result = _deterministic_fallback(warnings)
        assert result["confidence"] == "MEDIUM"

    def test_multiple_errors(self) -> None:
        warnings = [
            {
                "rule": "BASE_PLUS_OPTIONS_VS_TOTAL",
                "severity": "ERROR",
                "message": "...",
            },
            {"rule": "BASE_TOTAL_SWAPPED", "severity": "ERROR", "message": "..."},
        ]
        result = _deterministic_fallback(warnings)
        assert result["confidence"] == "LOW"
        # BASE_TOTAL_SWAPPED takes priority
        assert "zamian" in result["verdict"].lower()


class TestGeneratePriceSummary:
    """Integration tests for generate_price_summary with mocked Gemini."""

    def test_no_warnings_skips_llm(self) -> None:
        """No warnings → deterministic HIGH, no LLM call."""
        validation = {"is_valid": True, "warnings": [], "parsed_prices": {}}
        card = {"brand": "Toyota", "model": "Corolla"}
        result = generate_price_summary(validation, card)
        assert result is not None
        assert result["confidence"] == "HIGH"

    @patch("core.pipeline_price_summary._call_flash")
    def test_with_warnings_calls_flash(self, mock_flash: MagicMock) -> None:
        """With warnings → calls Flash."""
        mock_flash.return_value = {
            "verdict": "LLM zamienił pola",
            "confidence": "LOW",
            "details": "Cena bazowa > total",
            "suggestions": ["Zamień pola"],
        }
        validation = {
            "is_valid": False,
            "warnings": [
                {"rule": "BASE_TOTAL_SWAPPED", "severity": "ERROR", "message": "..."},
            ],
            "parsed_prices": {"base": 180170, "options": 35660, "total": 145750},
        }
        card = {"brand": "VW", "model": "Crafter"}
        result = generate_price_summary(validation, card)
        assert result is not None
        assert result["confidence"] == "LOW"
        mock_flash.assert_called_once()

    @patch("core.pipeline_price_summary._call_flash")
    def test_flash_failure_uses_fallback(self, mock_flash: MagicMock) -> None:
        """Flash exception → deterministic fallback, no crash."""
        mock_flash.side_effect = Exception("API timeout")
        validation = {
            "is_valid": False,
            "warnings": [
                {
                    "rule": "OPTION_PRICE_UNPARSEABLE",
                    "severity": "WARNING",
                    "message": "...",
                },
            ],
            "parsed_prices": {},
        }
        card = {"brand": "MarkaX", "model": "ModelY"}
        result = generate_price_summary(validation, card)
        assert result is not None
        assert result["confidence"] == "MEDIUM"
        # Should NOT crash

    def test_empty_validation_dict(self) -> None:
        """Edge case: empty validation dict."""
        result = generate_price_summary({}, {})
        assert result is not None
        assert result["confidence"] == "HIGH"
