"""Testy deterministycznego backfillu rabatu — bez DB i LLM."""

from __future__ import annotations

import pytest

from core.discount_backfill import (
    _find_explicit_rabat_pct,
    _find_explicit_rabat_pln,
    _parse_pl_number,
    _sum_dealer_extras,
    _sum_factory_options,
    apply_backfill_to_card_summary,
    derive_discount_breakdown,
)


# ═══════════════════════════════════════════════════════════════════
# Number parsing
# ═══════════════════════════════════════════════════════════════════


class TestParsePlNumber:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("42 317", 42317.0),
            ("42 317,50", 42317.50),
            ("42.317,00", 42317.0),
            ("1 000 000,00", 1000000.0),
            ("100", 100.0),
            ("0,5", 0.5),
        ],
    )
    def test_polish_format(self, input_str: str, expected: float) -> None:
        assert _parse_pl_number(input_str) == pytest.approx(expected)

    def test_invalid_returns_none(self) -> None:
        assert _parse_pl_number("abc") is None
        assert _parse_pl_number("") is None


# ═══════════════════════════════════════════════════════════════════
# RABAT regex extraction
# ═══════════════════════════════════════════════════════════════════


class TestFindExplicitRabatPln:
    def test_ford_format(self) -> None:
        text = "RABAT 42 317,-"
        assert _find_explicit_rabat_pln(text) == pytest.approx(42317)

    def test_with_pln(self) -> None:
        text = "Rabat dealerski: 15 000 PLN"
        assert _find_explicit_rabat_pln(text) == pytest.approx(15000)

    def test_with_zlotych(self) -> None:
        text = "Upust 12 500 zł"
        assert _find_explicit_rabat_pln(text) == pytest.approx(12500)

    def test_picks_largest_when_multiple(self) -> None:
        """Dokument może mieć rabat klienta + rabat dealera — wybierz większy."""
        text = "Rabat klienta 5 000 PLN. Bonus 100 PLN. RABAT 42 317"
        assert _find_explicit_rabat_pln(text) == pytest.approx(42317)

    def test_no_rabat_returns_none(self) -> None:
        assert _find_explicit_rabat_pln("Po prostu cena 100 000 PLN") is None

    def test_filters_unrealistic_values(self) -> None:
        """Liczba <100 lub >1M nie jest rabatem."""
        assert _find_explicit_rabat_pln("Rabat 50") is None
        assert _find_explicit_rabat_pln("Rabat 9999999999") is None


class TestFindExplicitRabatPct:
    def test_basic(self) -> None:
        assert _find_explicit_rabat_pct("Rabat 24%") == pytest.approx(24)

    def test_decimal(self) -> None:
        assert _find_explicit_rabat_pct("Rabat 12,5%") == pytest.approx(12.5)

    def test_filters_unrealistic(self) -> None:
        """Procenty muszą być w zakresie 0.5 - 60."""
        assert _find_explicit_rabat_pct("Rabat 0,1%") is None
        assert _find_explicit_rabat_pct("Rabat 80%") is None


# ═══════════════════════════════════════════════════════════════════
# Dealer extras summation
# ═══════════════════════════════════════════════════════════════════


class TestSumDealerExtras:
    def test_zabudowa_detected(self) -> None:
        opts = [
            {"name": "ZABUDOWA TYPU WYWROTKA", "price": "31 732 PLN", "category": "Dealer"},
            {"name": "Lakier metalik", "price": "3000 PLN", "category": "Fabryczna"},
        ]
        total, names = _sum_dealer_extras(opts)
        assert total == pytest.approx(31732)
        assert any("ZABUDOWA" in n.upper() for n in names)

    def test_pure_factory_no_extras(self) -> None:
        opts = [
            {"name": "Pakiet Premium", "price": "5000 PLN", "category": "Fabryczna"},
        ]
        total, names = _sum_dealer_extras(opts)
        assert total == 0
        assert names == []

    def test_kontener_izoterma_chlodnia(self) -> None:
        opts = [
            {"name": "Zabudowa kontenerowa", "price": "20000", "category": ""},
            {"name": "Izolacja izoterm", "price": "5000", "category": ""},
            {"name": "Agregat chłodniczy", "price": "8000", "category": ""},
        ]
        # "kontener" matches, "izoterm" matches, "chłodnia" doesn't match (chlodni instead)
        total, _ = _sum_dealer_extras(opts)
        assert total >= 25000  # kontener + izoterm certainly

    def test_factory_options_sum_excludes_dealer(self) -> None:
        opts = [
            {"name": "Lakier metalik", "price": "3000 PLN", "category": "Fabryczna"},
            {"name": "ZABUDOWA WYWROTKA", "price": "31732 PLN", "category": "Dealer"},
        ]
        factory = _sum_factory_options(opts)
        assert factory == pytest.approx(3000)


# ═══════════════════════════════════════════════════════════════════
# Full backfill — Ford Trakcja end-to-end
# ═══════════════════════════════════════════════════════════════════


class TestDeriveDiscountBreakdown:
    def _build_ford_case(self) -> tuple[dict, dict]:
        """Reprodukcja oferty Ford Trakcja OFERTA/9142/2026/04."""
        card_summary = {
            "base_price": "142 760 PLN netto",
            "options_price": "2725 PLN netto",
            "total_price": "134 900 PLN netto",
            "paid_options": [
                {"name": "Hak holowniczy", "price": "2000 PLN netto", "category": "Fabryczna"},
                {"name": "Koło zapasowe", "price": "625 PLN netto", "category": "Fabryczna"},
                {"name": "Dwa kluczyki", "price": "100 PLN netto", "category": "Fabryczna"},
                {
                    "name": "ZABUDOWA TYPU WYWROTKA",
                    "price": "31 732 PLN netto",
                    "category": "Dodatkowe wyposażenie dealera",
                },
            ],
        }
        digital_twin = {
            "summary": {
                "subtotal": "142 760",
                "rabat_line": "RABAT 42 317,-",
                "total": "CENA CAŁKOWITA POJAZDU Z RABATEM 134 900,-",
            },
        }
        return card_summary, digital_twin

    def test_ford_explicit_rabat_extracted_with_high_confidence(self) -> None:
        card_summary, digital_twin = self._build_ford_case()
        bd = derive_discount_breakdown(card_summary, digital_twin)
        assert bd is not None
        assert bd.extraction_method.value == "explicit_amount"
        assert bd.explicit_rabat_pln == pytest.approx(42317)
        # discountable = base + factory opts = 142760 + 2725
        assert bd.discountable_base_net == pytest.approx(145485)
        assert bd.non_discountable_total_net == pytest.approx(31732)
        assert bd.computed_pct == pytest.approx(29.08, abs=0.1)
        assert bd.confidence >= 0.85

    def test_apply_skips_when_explicit_already_present(self) -> None:
        """Idempotencja idzie przez apply_backfill_to_card_summary, nie derive."""
        card_summary, digital_twin = self._build_ford_case()
        card_summary["discount"] = {
            "explicit_rabat_pln": 42317,
            "extraction_method": "explicit_amount",
            "computed_pct": 29.08,
            "confidence": 1.0,
        }
        # derive ZAWSZE robi swoja prace (pure function)
        bd = derive_discount_breakdown(card_summary, digital_twin)
        assert bd is not None
        # ale apply skipuje gdy istnieje explicit_amount i overwrite_existing=False
        changed = apply_backfill_to_card_summary(card_summary, digital_twin, overwrite_existing=False)
        assert changed is False
        # Stary breakdown nienaruszony
        assert card_summary["discount"]["explicit_rabat_pln"] == 42317

    def test_implied_when_no_rabat_keyword(self) -> None:
        """Brak 'RABAT' w dokumencie → wyliczamy z różnicy total - (base + opcje)."""
        card_summary = {
            "base_price": "100 000 PLN netto",
            "options_price": "5 000 PLN netto",
            "total_price": "85 000 PLN netto",  # implied rabat = 20 000
            "paid_options": [],
        }
        bd = derive_discount_breakdown(card_summary, {})
        assert bd is not None
        assert bd.extraction_method.value == "computed_from_total"
        assert bd.explicit_rabat_pln == pytest.approx(20000)
        assert bd.confidence == pytest.approx(0.55)

    def test_no_signal_returns_none(self) -> None:
        """Cena bazowa = total + brak rabatu → nic nie wnioskujemy."""
        card_summary = {
            "base_price": "100 000 PLN netto",
            "total_price": "100 000 PLN netto",
        }
        assert derive_discount_breakdown(card_summary, {}) is None


# ═══════════════════════════════════════════════════════════════════
# apply_backfill_to_card_summary integration
# ═══════════════════════════════════════════════════════════════════


class TestApplyBackfill:
    def test_writes_discount_and_legacy_fields(self) -> None:
        card_summary = {
            "base_price": "100 000 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "85 000 PLN netto",
        }
        digital_twin = {"text": "Rabat klienta 15 000 PLN"}
        changed = apply_backfill_to_card_summary(card_summary, digital_twin)
        assert changed is True
        assert "discount" in card_summary
        assert card_summary["discount"]["explicit_rabat_pln"] == pytest.approx(15000)
        # Legacy fields populated for backward compat
        assert card_summary.get("offer_discount_pct") == "15.0"
        assert "15000" in card_summary.get("offer_discount_pln", "")

    def test_idempotent_when_existing_explicit(self) -> None:
        card_summary = {
            "base_price": "100 000 PLN netto",
            "discount": {
                "explicit_rabat_pln": 5000,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        changed = apply_backfill_to_card_summary(card_summary, {"text": "Rabat 999 PLN"})
        assert changed is False
        assert card_summary["discount"]["explicit_rabat_pln"] == 5000

    def test_overwrite_flag(self) -> None:
        card_summary = {
            "base_price": "100 000 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "85 000 PLN netto",
            "discount": {
                "explicit_rabat_pln": 999,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        changed = apply_backfill_to_card_summary(
            card_summary, {"text": "Rabat klienta 15 000 PLN"}, overwrite_existing=True
        )
        assert changed is True
        assert card_summary["discount"]["explicit_rabat_pln"] == pytest.approx(15000)
