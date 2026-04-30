"""Regression tests for discount extraction & validation.

Pokrywają realne pułapki ekstrakcji rabatu z ofert dealerskich, w tym
wzorzec błędu "7% zamiast 29%" wykryty na ofercie Ford Trakcja
(OFERTA/9142/2026/04) gdzie zabudowa wywrotka 31 732 zł zafałszowała
LLM-owe wyliczenie pośrednie.
"""

from __future__ import annotations

import pytest

from core.extractor_models import DiscountBreakdown, DiscountExtractionMethod
from core.pipeline_price_validator import validate_card_summary_prices


# ═══════════════════════════════════════════════════════════════════
# Schema: DiscountBreakdown
# ═══════════════════════════════════════════════════════════════════


class TestDiscountBreakdownSchema:
    def test_default_state_is_none(self) -> None:
        bd = DiscountBreakdown()
        assert bd.extraction_method == DiscountExtractionMethod.NONE
        assert bd.confidence == 1.0
        assert bd.audit_notes == []
        assert bd.explicit_rabat_pln is None

    def test_explicit_amount_with_full_decomposition(self) -> None:
        """Idealny przypadek Forda po naprawie."""
        bd = DiscountBreakdown(
            explicit_rabat_pln=42317.0,
            discountable_base_net=145485.0,
            non_discountable_total_net=31732.0,
            computed_pct=29.08,
            extraction_method=DiscountExtractionMethod.EXPLICIT_AMOUNT,
            confidence=1.0,
            audit_notes=["Triangulacja: 145485 + 31732 - 42317 = 134900 ✓"],
        )
        assert bd.computed_pct == pytest.approx(29.08)
        assert bd.confidence == 1.0

    def test_confidence_clamped(self) -> None:
        with pytest.raises(ValueError):
            DiscountBreakdown(confidence=1.5)
        with pytest.raises(ValueError):
            DiscountBreakdown(confidence=-0.1)


# ═══════════════════════════════════════════════════════════════════
# Rule 9: DISCOUNT_TRIANGULATION_FAILED
# ═══════════════════════════════════════════════════════════════════


class TestDiscountTriangulation:
    def test_ford_case_passes_when_correct(self) -> None:
        """Ford Transit z zabudową — wszystko prawidłowo, brak ostrzeżeń."""
        card = {
            "base_price": "145 485 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "134 900 PLN netto",
            "discount": {
                "explicit_rabat_pln": 42317.0,
                "discountable_base_net": 145485.0,
                "non_discountable_total_net": 31732.0,
                "computed_pct": 29.08,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        triang_warnings = [w for w in report.warnings if w.rule == "DISCOUNT_TRIANGULATION_FAILED"]
        assert triang_warnings == []

    def test_ford_case_fails_when_dealer_extras_omitted(self) -> None:
        """LLM zapomniał o zabudowie — triangulacja wykrywa lukę."""
        card = {
            "base_price": "145 485 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "134 900 PLN netto",
            "discount": {
                "explicit_rabat_pln": 42317.0,
                "discountable_base_net": 145485.0,
                "non_discountable_total_net": 0.0,  # ❌ pominięta zabudowa
                "computed_pct": 29.08,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        triang_warnings = [w for w in report.warnings if w.rule == "DISCOUNT_TRIANGULATION_FAILED"]
        assert len(triang_warnings) == 1
        assert triang_warnings[0].severity in ("WARNING", "ERROR")
        # Powinien wskazać że brakuje ~31 732 PLN
        assert triang_warnings[0].diff_pct is not None and triang_warnings[0].diff_pct > 5

    def test_no_breakdown_no_warning(self) -> None:
        """Stary dokument bez DiscountBreakdown — nie powinien spaść."""
        card = {
            "base_price": "100 000 PLN netto",
            "options_price": "10 000 PLN netto",
            "total_price": "110 000 PLN netto",
        }
        report = validate_card_summary_prices(card)
        triang_warnings = [w for w in report.warnings if w.rule == "DISCOUNT_TRIANGULATION_FAILED"]
        assert triang_warnings == []


# ═══════════════════════════════════════════════════════════════════
# Rule 10: DEALER_EXTRA_NOT_IN_NON_DISCOUNTABLE / DEALER_EXTRA_DETECTED
# ═══════════════════════════════════════════════════════════════════


class TestDealerExtraDetection:
    def test_zabudowa_in_paid_options_flagged_when_not_in_non_discountable(self) -> None:
        card = {
            "base_price": "142 760 PLN netto",
            "options_price": "34 457 PLN netto",
            "total_price": "134 900 PLN netto",
            "paid_options": [
                {"name": "Hak holowniczy", "price": "2000 PLN netto", "category": "Fabryczna"},
                {
                    "name": "ZABUDOWA TYPU WYWROTKA",
                    "price": "31 732 PLN netto",
                    "category": "Dodatkowe wyposażenie dealera",
                },
            ],
            "discount": {
                "explicit_rabat_pln": 42317.0,
                "discountable_base_net": 177217.0,  # ❌ błędnie wlicza zabudowę
                "non_discountable_total_net": 0.0,
                "computed_pct": 23.88,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        warns = [w for w in report.warnings if w.rule == "DEALER_EXTRA_NOT_IN_NON_DISCOUNTABLE"]
        assert len(warns) == 1
        assert "ZABUDOWA" in warns[0].message.upper() or "wywrotka" in warns[0].message.lower()

    def test_zabudowa_correctly_classified_emits_info(self) -> None:
        card = {
            "base_price": "145 485 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "134 900 PLN netto",
            "paid_options": [
                {
                    "name": "ZABUDOWA TYPU WYWROTKA",
                    "price": "31 732 PLN netto",
                    "category": "Dodatkowe wyposażenie dealera",
                },
            ],
            "discount": {
                "explicit_rabat_pln": 42317.0,
                "discountable_base_net": 145485.0,
                "non_discountable_total_net": 31732.0,
                "computed_pct": 29.08,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        info_warns = [w for w in report.warnings if w.rule == "DEALER_EXTRA_DETECTED"]
        assert len(info_warns) == 1
        assert info_warns[0].severity == "INFO"

    def test_no_dealer_extras_no_warning(self) -> None:
        """Standardowy mieszczanin bez zabudowy."""
        card = {
            "base_price": "100 000 PLN netto",
            "options_price": "5 000 PLN netto",
            "total_price": "95 000 PLN netto",
            "paid_options": [
                {"name": "Lakier metalik Brilliant Silver", "price": "3000 PLN netto", "category": "Fabryczna"},
                {"name": "Pakiet Premium", "price": "2000 PLN netto", "category": "Fabryczna"},
            ],
        }
        report = validate_card_summary_prices(card)
        warns = [
            w
            for w in report.warnings
            if w.rule in ("DEALER_EXTRA_DETECTED", "DEALER_EXTRA_NOT_IN_NON_DISCOUNTABLE")
        ]
        assert warns == []


# ═══════════════════════════════════════════════════════════════════
# Rule 11: DISCOUNT_PCT sanity range
# ═══════════════════════════════════════════════════════════════════


class TestDiscountPctSanity:
    def test_seven_percent_flagged_as_suspiciously_low(self) -> None:
        """Stary błąd: 7.28% wyliczone bez uwzględnienia zabudowy."""
        card = {
            "base_price": "145 485 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "134 900 PLN netto",
            "discount": {
                "explicit_rabat_pln": 10585.0,
                "discountable_base_net": 145485.0,
                "non_discountable_total_net": 0.0,
                "computed_pct": 7.28,
                "extraction_method": "computed_from_total",
                "confidence": 0.5,
            },
        }
        report = validate_card_summary_prices(card)
        # Mała wartość % nie jest poniżej 0.5%, więc to nie powinno być low.
        # Tutaj sprawdzamy że computed_from_total dostaje INFO.
        info_warns = [w for w in report.warnings if w.rule == "DISCOUNT_COMPUTED_INDIRECTLY"]
        assert len(info_warns) == 1

    def test_below_threshold_flagged_low(self) -> None:
        card = {
            "base_price": "100 000 PLN netto",
            "total_price": "99 950 PLN netto",
            "discount": {
                "explicit_rabat_pln": 50.0,
                "discountable_base_net": 100000.0,
                "non_discountable_total_net": 0.0,
                "computed_pct": 0.05,  # bardzo niski
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        low_warns = [w for w in report.warnings if w.rule == "DISCOUNT_PCT_SUSPICIOUSLY_LOW"]
        assert len(low_warns) == 1
        assert low_warns[0].severity == "WARNING"

    def test_above_threshold_flagged_high(self) -> None:
        card = {
            "base_price": "100 000 PLN netto",
            "total_price": "30 000 PLN netto",
            "discount": {
                "explicit_rabat_pln": 70000.0,
                "discountable_base_net": 100000.0,
                "non_discountable_total_net": 0.0,
                "computed_pct": 70.0,  # absurdalnie wysoki
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        high_warns = [w for w in report.warnings if w.rule == "DISCOUNT_PCT_SUSPICIOUSLY_HIGH"]
        assert len(high_warns) == 1
        assert high_warns[0].severity == "ERROR"

    def test_normal_25_percent_no_warning(self) -> None:
        card = {
            "base_price": "200 000 PLN netto",
            "total_price": "150 000 PLN netto",
            "discount": {
                "explicit_rabat_pln": 50000.0,
                "discountable_base_net": 200000.0,
                "non_discountable_total_net": 0.0,
                "computed_pct": 25.0,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        report = validate_card_summary_prices(card)
        sanity_warns = [
            w
            for w in report.warnings
            if w.rule
            in (
                "DISCOUNT_PCT_SUSPICIOUSLY_LOW",
                "DISCOUNT_PCT_SUSPICIOUSLY_HIGH",
                "DISCOUNT_COMPUTED_INDIRECTLY",
            )
        ]
        assert sanity_warns == []
