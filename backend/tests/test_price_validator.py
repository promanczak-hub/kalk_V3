"""Tests for core.pipeline_price_validator — financial consistency checks."""

from core.pipeline_price_validator import (
    ValidationReport,
    ValidationWarning,
    _detect_via_vat_arithmetic,
    _propagate_domain_to_options,
    detect_and_normalize_price_domain,
    validate_and_flag_prices,
    validate_card_summary_prices,
)


# ═══════════════════════════════════════════════════════════════════
# Rule 12: NET/GROSS ratio sanity per item
# ═══════════════════════════════════════════════════════════════════


class TestNetGrossRatioPerItem:
    def _card_with_se(self, net: str, gross: str) -> dict:
        return {
            "base_price": "100000 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "100000 PLN netto",
            "service_equipment": {
                "name": "Test zabudowa",
                "total_price_net": net,
                "total_price_gross": gross,
                "components": [],
            },
        }

    def test_correct_ratio_no_warning(self) -> None:
        card = self._card_with_se("10000 PLN", "12300 PLN")
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "NET_GROSS_RATIO_INVALID"]
        assert flagged == []

    def test_same_value_in_both_fields_flagged(self) -> None:
        """AI dała te same kwoty do net i gross — ratio = 1.0."""
        card = self._card_with_se("47970 PLN", "47970 PLN")
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "NET_GROSS_RATIO_INVALID"]
        assert len(flagged) == 1
        assert flagged[0].severity == "WARNING"

    def test_wrong_ratio_flagged(self) -> None:
        """ratio = 1.5 zamiast 1.23."""
        card = self._card_with_se("10000 PLN", "15000 PLN")
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "NET_GROSS_RATIO_INVALID"]
        assert len(flagged) == 1

    def test_each_component_checked(self) -> None:
        card = self._card_with_se("10000 PLN", "12300 PLN")
        card["service_equipment"]["components"] = [
            {"name": "OK comp", "price_net": "5000 PLN", "price_gross": "6150 PLN"},
            {"name": "BAD comp", "price_net": "5000 PLN", "price_gross": "5000 PLN"},
        ]
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "NET_GROSS_RATIO_INVALID"]
        assert len(flagged) == 1
        assert "BAD comp" in flagged[0].message


# ═══════════════════════════════════════════════════════════════════
# Rule 13: service_equipment.total ≈ sum(components)
# ═══════════════════════════════════════════════════════════════════


class TestServiceEquipmentSumIntegrity:
    def test_matching_sum_no_warning(self) -> None:
        card = {
            "base_price": "100000 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "100000 PLN netto",
            "service_equipment": {
                "name": "Test",
                "total_price_net": "10000 PLN",
                "total_price_gross": "12300 PLN",
                "components": [
                    {"name": "A", "price_net": "6000 PLN", "price_gross": "7380 PLN"},
                    {"name": "B", "price_net": "4000 PLN", "price_gross": "4920 PLN"},
                ],
            },
        }
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "SERVICE_EQUIPMENT_SUM_MISMATCH"]
        assert flagged == []

    def test_mismatched_sum_flagged(self) -> None:
        card = {
            "base_price": "100000 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "100000 PLN netto",
            "service_equipment": {
                "name": "Test",
                "total_price_net": "10000 PLN",
                "total_price_gross": "12300 PLN",
                "components": [
                    {"name": "A", "price_net": "6000 PLN", "price_gross": "7380 PLN"},
                    {"name": "B", "price_net": "3500 PLN", "price_gross": "4305 PLN"},
                ],
            },
        }
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "SERVICE_EQUIPMENT_SUM_MISMATCH"]
        assert len(flagged) == 2  # net + gross both flagged
        assert any("netto" in w.message for w in flagged)
        assert any("brutto" in w.message for w in flagged)


# ═══════════════════════════════════════════════════════════════════
# _apply_self_healing — options_price recalc z uwzględnieniem rabatu
# ═══════════════════════════════════════════════════════════════════


class TestAutoFixOptionsPrice:
    """Fix dla bug'a: AI / pipeline wpisuje options_price jako total - base,
    ignorując rabat i zabudowę. Pełne równanie:
        options = total + rabat - non_discountable - base
    """

    def test_master_izoterma_real_case(self) -> None:
        """Realny case ccc626be Master: options_price powinno być 2029.50
        (suma fabrycznych opcji), nie 37598 (total - base)."""
        card = {
            "base_price": "167218.50 PLN netto",
            "options_price": "Brak",  # AI nie dała — pipeline naprawia
            "total_price": "204817.14 PLN netto",
            "paid_options": [
                {
                    "name": "Pakiet Conversion 2",
                    "price": "738.00 PLN netto",
                    "category": "Fabryczna",
                },
                {
                    "name": "światła przeciwmgłowe",
                    "price": "738.00 PLN netto",
                    "category": "Fabryczna",
                },
                {
                    "name": "asystent świateł",
                    "price": "553.50 PLN netto",
                    "category": "Fabryczna",
                },
            ],
            "discount": {
                "explicit_rabat_pln": 49928.16,
                "discountable_base_net": 169248.0,
                "non_discountable_total_net": 85497.30,
                "extraction_method": "computed_from_total",
                "confidence": 0.5,
            },
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]
        # 204817.14 + 49928.16 - 85497.30 - 167218.50 = 2029.50
        # Pole options_price ma zawierać liczbę bliską 2029
        opts = cs["options_price"]
        assert "2029" in opts or "2030" in opts  # int() rounding may vary
        assert "netto" in opts.lower()

    def test_simple_case_without_discount_falls_back(self) -> None:
        """Bez discount field — używa klasycznego total - base."""
        card = {
            "base_price": "100000 PLN netto",
            "options_price": "999999 PLN netto",  # nieprawidłowa wartość
            "total_price": "120000 PLN netto",
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]
        # 120000 - 100000 = 20000 (no discount → classic formula)
        assert "20000" in cs["options_price"]

    def test_negative_correction_blocks_self_heal(self) -> None:
        """Gdy `total + rabat - non_disc - base` < 0 → nie nadpisuj options
        ujemną wartością; pozostaw warning żeby user/lejek mógł zareagować."""
        # Pełne równanie: options = 100000 + 0 - 500000 - 200000 = -600000 < 0
        card = {
            "base_price": "200000 PLN netto",
            "options_price": "Brak",
            "total_price": "100000 PLN netto",
            "discount": {
                "explicit_rabat_pln": 0,
                "non_discountable_total_net": 500000,  # absurdalnie wysoka — wymusza negative
            },
        }
        result = validate_and_flag_prices({"card_summary": card})
        rules = [
            w["rule"] for w in result["card_summary"]["_validation"]["warnings"]
        ]
        # Bezpieczeństwo: AUTO_FIX_APPLIED NIE pojawia się dla ujemnego wyniku
        assert "AUTO_FIX_APPLIED" not in rules


# ═══════════════════════════════════════════════════════════════════
# _apply_self_healing — derive base_price gdy LLM nie znalazł go w PDF
# ═══════════════════════════════════════════════════════════════════


class TestAutoDeriveBasePrice:
    """Symetryczny self-heal: gdy LLM nie znalazł base_price w dokumencie
    (np. Audi drukuje tylko cenę końcową + opcje), validator deterministycznie
    wylicza bazę jako `total + rabat − non_discountable − options`.
    """

    def test_base_auto_derived_happy_path(self) -> None:
        """Audi-like case: base brak, total + options spójne, brak rabatu.
        Oczekiwane: derived_base = 120000 − 20000 = 100000."""
        card = {
            "base_price": "Brak",
            "options_price": "20000 PLN netto",
            "total_price": "120000 PLN netto",
            "paid_options": [
                {"name": "Pakiet komfort", "price": "12000 PLN netto", "category": "Fabryczna"},
                {"name": "Lakier metalik", "price": "8000 PLN netto", "category": "Fabryczna"},
            ],
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]

        assert cs["_base_derived"] is True
        assert "100000" in cs["base_price"]
        assert "netto" in cs["base_price"].lower()

        rules = [w["rule"] for w in cs["_validation"]["warnings"]]
        assert "BASE_AUTO_DERIVED" in rules

        # Wyliczona baza ląduje w parsed_prices.base, więc gate w phase_2_mapping
        # puści rekord do enrichment'u zamiast zatrzymać w needs_review.
        assert cs["_validation"]["parsed_prices"]["base"] == 100000

        # INFO severity → is_valid pozostaje True
        derived_warnings = [
            w for w in cs["_validation"]["warnings"] if w["rule"] == "BASE_AUTO_DERIVED"
        ]
        assert derived_warnings[0]["severity"] == "INFO"

    def test_base_auto_derived_blocked_by_options_mismatch(self) -> None:
        """Gdy sum(paid_options) ≠ declared options_price, NIE wyliczamy bazy
        — sygnał że options jest niepełne, więc derived base byłaby zawyżona."""
        card = {
            "base_price": "Brak",
            "options_price": "20000 PLN netto",
            "total_price": "120000 PLN netto",
            "paid_options": [
                # tylko 18000 zamiast 20000 — mismatch wystrzeli
                {"name": "Pakiet komfort", "price": "18000 PLN netto", "category": "Fabryczna"},
            ],
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]

        assert cs.get("_base_derived") is not True
        # base_price nadal "Brak" (nie zostało nadpisane)
        assert "Brak" in cs["base_price"] or cs["base_price"] == "Brak"

        rules = [w["rule"] for w in cs["_validation"]["warnings"]]
        assert "OPTIONS_SUM_MISMATCH" in rules
        assert "BASE_AUTO_DERIVED" not in rules

        # parsed_base nadal None → gate zatrzyma w needs_review (zachowanie jak dziś)
        assert cs["_validation"]["parsed_prices"]["base"] is None

    def test_base_auto_derived_with_discount(self) -> None:
        """Realny case z rabatem i zabudową (analogicznie do przykładu z promptu):
        total=134900, options=2725 (factory), rabat=42317, non_disc=31732 (zabudowa).
        derived_base = 134900 + 42317 − 31732 − 2725 = 142760."""
        card = {
            "base_price": "Brak",
            "options_price": "2725 PLN netto",
            "total_price": "134900 PLN netto",
            "paid_options": [
                {"name": "Hak fabryczny", "price": "2725 PLN netto", "category": "Fabryczna"},
            ],
            "discount": {
                "explicit_rabat_pln": 42317.0,
                "discountable_base_net": 145485.0,
                "non_discountable_total_net": 31732.0,
                "extraction_method": "explicit_amount",
                "confidence": 1.0,
            },
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]

        assert cs["_base_derived"] is True
        assert "142760" in cs["base_price"]
        assert cs["_validation"]["parsed_prices"]["base"] == 142760.0

    def test_base_auto_derived_blocked_by_unknown_domain(self) -> None:
        """Gdy domena cenowa nie da się ustalić (brak suffixów netto/brutto,
        brak relacji VAT) → nie wyliczamy bazy, żeby uniknąć mieszania domen."""
        # 150k i 130k nie są ze sobą w relacji ×1.23, brak suffixów
        card = {
            "base_price": "Brak",
            "options_price": "20000 PLN",
            "total_price": "150000 PLN",
            "paid_options": [
                {"name": "Opcja", "price": "20000 PLN", "category": "Fabryczna"},
            ],
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]

        assert cs.get("_base_derived") is not True
        rules = [w["rule"] for w in cs["_validation"]["warnings"]]
        assert "BASE_AUTO_DERIVED" not in rules

    def test_base_derivation_out_of_range_flagged(self) -> None:
        """Gdy derived_base byłoby ujemne lub <30% total → flag ERROR,
        nie nadpisuj bazy. Tu: options ≈ total, więc derived_base ≈ 0."""
        card = {
            "base_price": "Brak",
            "options_price": "119000 PLN netto",
            "total_price": "120000 PLN netto",
            "paid_options": [
                {"name": "Megapakiet", "price": "119000 PLN netto", "category": "Fabryczna"},
            ],
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]

        assert cs.get("_base_derived") is not True
        rules = [w["rule"] for w in cs["_validation"]["warnings"]]
        assert "BASE_DERIVATION_OUT_OF_RANGE" in rules
        # parsed_base nadal None
        assert cs["_validation"]["parsed_prices"]["base"] is None


# ═══════════════════════════════════════════════════════════════════
# Rule 2: base + options ≈ total
# ═══════════════════════════════════════════════════════════════════


class TestSumConsistency:
    """Rule: base + options ≈ total (tolerance 0.2%)."""

    def test_consistent_prices_pass(self) -> None:
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "25 000 PLN brutto",
            "total_price": "205 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is True
        no_sum_warnings = [
            w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"
        ]
        assert len(no_sum_warnings) == 0

    def test_hallucinated_total_detected(self) -> None:
        """AI returned total that doesn't match base + options (>1% = ERROR)."""
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "25 000 PLN brutto",
            "total_price": "190 000 PLN brutto",  # 180k+25k=205k ≠ 190k
        }
        report = validate_card_summary_prices(card)
        sum_warnings = [
            w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"
        ]
        assert len(sum_warnings) == 1
        assert sum_warnings[0].severity == "ERROR"  # >1% → ERROR
        assert sum_warnings[0].diff_pct is not None
        assert sum_warnings[0].diff_pct > 1.0

    def test_large_discrepancy_is_error(self) -> None:
        """More than 1% difference should be ERROR severity."""
        card = {
            "base_price": "200 000 PLN brutto",
            "options_price": "30 000 PLN brutto",
            "total_price": "150 000 PLN brutto",  # 230k vs 150k = 34.8%
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is False
        errors = [w for w in report.warnings if w.severity == "ERROR"]
        assert len(errors) >= 1

    def test_discount_above_2_promille_is_flagged(self) -> None:
        """With 2‰ tolerance, even a 2.3% discount is flagged."""
        card = {
            "base_price": "200 000 PLN brutto",
            "options_price": "20 000 PLN brutto",
            "total_price": "215 000 PLN brutto",  # 220k vs 215k = 2.3%
        }
        report = validate_card_summary_prices(card)
        sum_warnings = [
            w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"
        ]
        assert len(sum_warnings) == 1  # 2.3% > 0.2% → flagged

    def test_within_2_promille_tolerance_passes(self) -> None:
        """Difference within 2‰ (0.2%) should be accepted."""
        card = {
            "base_price": "200 000 PLN brutto",
            "options_price": "20 000 PLN brutto",
            "total_price": "220 400 PLN brutto",  # 220k vs 220.4k = 0.18%
        }
        report = validate_card_summary_prices(card)
        sum_warnings = [
            w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"
        ]
        assert len(sum_warnings) == 0

    def test_missing_options_treated_as_zero(self) -> None:
        """When options_price is Brak, treat as 0."""
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "Brak",
            "total_price": "180 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is True

    def test_netto_brutto_mismatch_detected(self) -> None:
        """base_price is Netto, total_price is Brutto → detected as VAT mismatch."""
        card = {
            "base_price": "100 000 PLN",
            "options_price": "0 PLN",
            "total_price": "123 000 PLN",
        }
        report = validate_card_summary_prices(card)
        warnings = [
            w
            for w in report.warnings
            if w.rule == "SUM_CONSISTENCY_NETTO_BRUTTO_MISMATCH"
        ]
        assert len(warnings) == 1
        assert warnings[0].severity == "WARNING"

    def test_brutto_netto_mismatch_detected(self) -> None:
        """base_price is Brutto, total_price is Netto → detected as VAT mismatch."""
        card = {
            "base_price": "123 000 PLN",
            "options_price": "0 PLN",
            "total_price": "100 000 PLN",  # Notice the price value order reversed
        }
        report = validate_card_summary_prices(card)
        warnings = [
            w
            for w in report.warnings
            if w.rule == "SUM_CONSISTENCY_BRUTTO_NETTO_MISMATCH"
        ]
        assert len(warnings) == 1
        assert warnings[0].severity == "WARNING"


class TestSumConsistencyEdge:
    """Edge cases for base + options ≈ total rule."""

    def test_exactly_at_02_pct_boundary(self) -> None:
        """Difference of exactly 0.2% should NOT trigger (tolerance is >)."""
        # base=100k, options=0, total must differ by 0.2%
        # 0.2% of 100k = 200 → total = 100_200 → exactly boundary
        card = {
            "base_price": "100 000 PLN brutto",
            "total_price": "100 200 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        sum_w = [w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"]
        assert len(sum_w) == 0  # exactly 0.2% → NOT flagged (> not >=)

    def test_just_above_02_pct_boundary(self) -> None:
        """Difference of 0.21% should trigger."""
        card = {
            "base_price": "100 000 PLN brutto",
            "total_price": "100 210 PLN brutto",  # 0.21% > 0.2%
        }
        report = validate_card_summary_prices(card)
        sum_w = [w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"]
        assert len(sum_w) == 1

    def test_both_base_and_total_none(self) -> None:
        """If base or total is None, skip sum check — no crash."""
        card: dict = {
            "base_price": None,
            "total_price": None,
        }
        report = validate_card_summary_prices(card)
        sum_w = [w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"]
        assert len(sum_w) == 0

    def test_options_none_total_equals_base(self) -> None:
        """No options → total should equal base. Exact match passes."""
        card = {
            "base_price": "150 000 PLN brutto",
            "total_price": "150 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        sum_w = [w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"]
        assert len(sum_w) == 0

    def test_warning_severity_between_02_and_1_pct(self) -> None:
        """Difference 0.5% = between 0.2% and 1% → WARNING (not ERROR)."""
        # 0.5% of 200k = 1000 → total = 201_000
        card = {
            "base_price": "200 000 PLN brutto",
            "total_price": "201 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        sum_w = [w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"]
        assert len(sum_w) == 1
        assert sum_w[0].severity == "WARNING"


# ═══════════════════════════════════════════════════════════════════
# Rule 1: Sanity — realistic price range
# ═══════════════════════════════════════════════════════════════════


class TestSanityChecks:
    """Rule: prices must be in realistic range (70k – 3M PLN)."""

    def test_suspiciously_low_price(self) -> None:
        card = {
            "base_price": "50 000 PLN brutto",
            "total_price": "50 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        low_warnings = [w for w in report.warnings if w.rule == "PRICE_TOO_LOW"]
        assert len(low_warnings) >= 1

    def test_suspiciously_high_price(self) -> None:
        card = {
            "base_price": "5 000 000 PLN brutto",
            "total_price": "5 000 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        high_warnings = [w for w in report.warnings if w.rule == "PRICE_TOO_HIGH"]
        assert len(high_warnings) >= 1


class TestSanityEdgeCases:
    """Edge cases for price sanity checks."""

    def test_exactly_at_min_boundary(self) -> None:
        """70 000 PLN is NOT suspicious (>= min threshold)."""
        card = {
            "base_price": "70 000 PLN brutto",
            "total_price": "70 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        low_w = [w for w in report.warnings if w.rule == "PRICE_TOO_LOW"]
        assert len(low_w) == 0

    def test_just_below_min_boundary(self) -> None:
        """69 999 PLN < 70k → PRICE_TOO_LOW."""
        card = {
            "base_price": "69 999 PLN brutto",
            "total_price": "69 999 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        low_w = [w for w in report.warnings if w.rule == "PRICE_TOO_LOW"]
        assert len(low_w) >= 1

    def test_exactly_at_max_boundary(self) -> None:
        """3 000 000 PLN is NOT suspicious (<= max threshold)."""
        card = {
            "base_price": "3 000 000 PLN brutto",
            "total_price": "3 000 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        high_w = [w for w in report.warnings if w.rule == "PRICE_TOO_HIGH"]
        assert len(high_w) == 0

    def test_just_above_max_boundary(self) -> None:
        """3 000 001 PLN > 3M → PRICE_TOO_HIGH."""
        card = {
            "base_price": "3 000 001 PLN brutto",
            "total_price": "3 000 001 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        high_w = [w for w in report.warnings if w.rule == "PRICE_TOO_HIGH"]
        assert len(high_w) >= 1

    def test_none_price_skips_sanity(self) -> None:
        """None / unparseable price → no sanity warning, no crash."""
        card: dict = {
            "base_price": None,
            "total_price": "Brak",
        }
        report = validate_card_summary_prices(card)
        sanity_w = [
            w for w in report.warnings if w.rule in ("PRICE_TOO_LOW", "PRICE_TOO_HIGH")
        ]
        assert len(sanity_w) == 0

    def test_negative_price_skips(self) -> None:
        """Negative price string → parse_price_string returns None → skip."""
        card = {
            "base_price": "-50 000 PLN",
            "total_price": "100 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        # Negative parsed as None by price_parser (value <= 0)
        assert report.parsed_base is None


# ═══════════════════════════════════════════════════════════════════
# Rule 3: sum(paid_options) ≈ options_price
# ═══════════════════════════════════════════════════════════════════


class TestOptionsCrossSum:
    """Rule: sum(paid_options.price) ≈ options_price."""

    def test_options_sum_matches(self) -> None:
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "10 000 PLN brutto",
            "total_price": "190 000 PLN brutto",
            "paid_options": [
                {"name": "Nawigacja", "price": "4 000 PLN", "category": "Fabryczna"},
                {"name": "Kamera", "price": "3 000 PLN", "category": "Fabryczna"},
                {"name": "Hak", "price": "3 000 PLN", "category": "Fabryczna"},
            ],
        }
        report = validate_card_summary_prices(card)
        mismatch = [w for w in report.warnings if w.rule == "OPTIONS_SUM_MISMATCH"]
        assert len(mismatch) == 0

    def test_options_sum_mismatch(self) -> None:
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "25 000 PLN brutto",
            "total_price": "205 000 PLN brutto",
            "paid_options": [
                {"name": "Nawigacja", "price": "4 000 PLN", "category": "Fabryczna"},
                {"name": "Kamera", "price": "3 000 PLN", "category": "Fabryczna"},
                # Total: 7k vs declared 25k → big mismatch
            ],
        }
        report = validate_card_summary_prices(card)
        mismatch = [w for w in report.warnings if w.rule == "OPTIONS_SUM_MISMATCH"]
        assert len(mismatch) == 1


class TestOptionsCrossSumEdge:
    """Edge cases for options cross-sum rule."""

    def test_empty_paid_options_list(self) -> None:
        """Empty paid_options → skip cross-sum check."""
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "10 000 PLN brutto",
            "total_price": "190 000 PLN brutto",
            "paid_options": [],
        }
        report = validate_card_summary_prices(card)
        mismatch = [w for w in report.warnings if w.rule == "OPTIONS_SUM_MISMATCH"]
        assert len(mismatch) == 0

    def test_options_with_unparseable_prices(self) -> None:
        """Options that have 'Brak' or None price → skip them gracefully."""
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "5 000 PLN brutto",
            "total_price": "185 000 PLN brutto",
            "paid_options": [
                {"name": "Nawigacja", "price": "Brak"},
                {"name": "Kamera", "price": "w cenie"},
            ],
        }
        report = validate_card_summary_prices(card)
        # No parseable options → skip rule entirely
        mismatch = [w for w in report.warnings if w.rule == "OPTIONS_SUM_MISMATCH"]
        assert len(mismatch) == 0

    def test_non_dict_option_is_skipped(self) -> None:
        """If paid_options contains non-dict items → skip gracefully."""
        card = {
            "base_price": "180 000 PLN brutto",
            "options_price": "5 000 PLN brutto",
            "total_price": "185 000 PLN brutto",
            "paid_options": ["some string", 123, None],
        }
        report = validate_card_summary_prices(card)
        # Should not crash
        mismatch = [w for w in report.warnings if w.rule == "OPTIONS_SUM_MISMATCH"]
        assert len(mismatch) == 0

    def test_declared_options_none_skips(self) -> None:
        """If options_price is None but paid_options present → skip."""
        card = {
            "base_price": "180 000 PLN brutto",
            "total_price": "185 000 PLN brutto",
            "paid_options": [
                {"name": "Hak", "price": "5 000 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        mismatch = [w for w in report.warnings if w.rule == "OPTIONS_SUM_MISMATCH"]
        assert len(mismatch) == 0


# ═══════════════════════════════════════════════════════════════════
# Rule 4: Single option > 50% of base
# ═══════════════════════════════════════════════════════════════════


class TestSingleOptionRatio:
    """Rule: no single option > 50% of base."""

    def test_expensive_option_flagged(self) -> None:
        card = {
            "base_price": "100 000 PLN brutto",
            "options_price": "60 000 PLN brutto",
            "total_price": "160 000 PLN brutto",
            "paid_options": [
                {"name": "Zabudowa", "price": "60 000 PLN", "category": "Serwisowa"},
            ],
        }
        report = validate_card_summary_prices(card)
        expensive = [
            w
            for w in report.warnings
            if w.rule == "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE"
        ]
        assert len(expensive) == 1


class TestSingleOptionRatioEdge:
    """Edge cases for single option ratio rule."""

    def test_option_exactly_50_pct_not_flagged(self) -> None:
        """50% of base is NOT flagged (rule is > 50%, not >=)."""
        card = {
            "base_price": "100 000 PLN brutto",
            "options_price": "50 000 PLN brutto",
            "total_price": "150 000 PLN brutto",
            "paid_options": [
                {"name": "Zabudowa", "price": "50 000 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        expensive = [
            w
            for w in report.warnings
            if w.rule == "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE"
        ]
        assert len(expensive) == 0  # exactly 50% → NOT flagged

    def test_option_just_above_50_pct(self) -> None:
        """50.01% of base IS flagged."""
        card = {
            "base_price": "100 000 PLN brutto",
            "options_price": "50 010 PLN brutto",
            "total_price": "150 010 PLN brutto",
            "paid_options": [
                {"name": "Zabudowa", "price": "50 010 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        expensive = [
            w
            for w in report.warnings
            if w.rule == "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE"
        ]
        assert len(expensive) == 1

    def test_base_none_skips_ratio_check(self) -> None:
        """If base_price is unparseable → skip ratio check."""
        card = {
            "base_price": "Brak",
            "options_price": "50 000 PLN brutto",
            "total_price": "150 000 PLN brutto",
            "paid_options": [
                {"name": "Zabudowa", "price": "50 000 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        expensive = [
            w
            for w in report.warnings
            if w.rule == "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE"
        ]
        assert len(expensive) == 0

    def test_multiple_cheap_options_no_flag(self) -> None:
        """Many small options below 50% each → no flag."""
        card = {
            "base_price": "200 000 PLN brutto",
            "options_price": "30 000 PLN brutto",
            "total_price": "230 000 PLN brutto",
            "paid_options": [
                {"name": "Hak", "price": "5 000 PLN"},
                {"name": "Kamera", "price": "8 000 PLN"},
                {"name": "Nawigacja", "price": "7 000 PLN"},
                {"name": "Czujniki", "price": "10 000 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        expensive = [
            w
            for w in report.warnings
            if w.rule == "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE"
        ]
        assert len(expensive) == 0


# ═══════════════════════════════════════════════════════════════════
# Rule 5: total < 50% base → hallucination
# ═══════════════════════════════════════════════════════════════════


class TestBaseVsTotal:
    """Rule: total should not be drastically below base."""

    def test_total_below_half_base(self) -> None:
        card = {
            "base_price": "200 000 PLN brutto",
            "total_price": "80 000 PLN brutto",  # < 50% of base
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is False
        below = [w for w in report.warnings if w.rule == "TOTAL_BELOW_BASE"]
        assert len(below) == 1


class TestBaseVsTotalEdge:
    """Edge cases for base vs total rule."""

    def test_total_exactly_50_pct_of_base(self) -> None:
        """total = exactly 50% of base → NOT flagged (rule is <)."""
        card = {
            "base_price": "200 000 PLN brutto",
            "total_price": "100 000 PLN brutto",  # exactly 50%
        }
        report = validate_card_summary_prices(card)
        below = [w for w in report.warnings if w.rule == "TOTAL_BELOW_BASE"]
        assert len(below) == 0

    def test_total_above_base_is_fine(self) -> None:
        """total > base → normal case, no flag."""
        card = {
            "base_price": "150 000 PLN brutto",
            "total_price": "180 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        below = [w for w in report.warnings if w.rule == "TOTAL_BELOW_BASE"]
        assert len(below) == 0


# ═══════════════════════════════════════════════════════════════════
# Price domain detection (netto/brutto)
# ═══════════════════════════════════════════════════════════════════


class TestPriceDomainDetection:
    """detect_and_normalize_price_domain() logic."""

    def test_netto_detected_from_label(self) -> None:
        """Explicit 'netto' in price string → detected."""
        card = {
            "base_price": "150 000 PLN netto",
            "total_price": "184 500 PLN brutto",
        }
        domain = detect_and_normalize_price_domain(card)
        assert domain == "netto"

    def test_brutto_detected_from_label(self) -> None:
        """Explicit 'brutto' in base_price → detected."""
        card = {
            "base_price": "200 000 PLN brutto",
            "total_price": "220 000 PLN brutto",
        }
        domain = detect_and_normalize_price_domain(card)
        assert domain == "brutto"

    def test_ai_declared_domain_used(self) -> None:
        """AI price_domain field used when labels are absent."""
        card = {
            "base_price": "150 000 PLN",
            "total_price": "180 000 PLN",
            "price_domain": "netto",
        }
        domain = detect_and_normalize_price_domain(card)
        assert domain == "netto"

    def test_vat_arithmetic_fallback(self) -> None:
        """When labels are absent, detect via VAT arithmetic."""
        # 150_000 × 1.23 = 184_500 → base is netto
        card = {
            "base_price": "150 000 PLN",
            "total_price": "184 500 PLN",
        }
        domain = detect_and_normalize_price_domain(card)
        assert domain == "netto"

    def test_unknown_when_no_clues(self) -> None:
        """No labels, no AI field, no VAT ratio → unknown."""
        card = {
            "base_price": "150 000 PLN",
            "total_price": "200 000 PLN",
        }
        domain = detect_and_normalize_price_domain(card)
        assert domain == "unknown"

    def test_label_priority_over_ai_field(self) -> None:
        """Explicit label in price string takes precedence over AI field."""
        card = {
            "base_price": "150 000 PLN netto",
            "total_price": "184 500 PLN",
            "price_domain": "brutto",  # AI says brutto, but label says netto
        }
        domain = detect_and_normalize_price_domain(card)
        assert domain == "netto"  # label wins


class TestVatArithmetic:
    """_detect_via_vat_arithmetic() unit tests."""

    def test_netto_to_brutto_ratio(self) -> None:
        """price_a × 1.23 ≈ price_b → 'netto'."""
        result = _detect_via_vat_arithmetic(100_000.0, 123_000.0)
        assert result == "netto"

    def test_brutto_to_netto_ratio(self) -> None:
        """price_b × 1.23 ≈ price_a → 'brutto'."""
        result = _detect_via_vat_arithmetic(123_000.0, 100_000.0)
        assert result == "brutto"

    def test_no_vat_relationship(self) -> None:
        """No VAT ratio between prices → 'unknown'."""
        result = _detect_via_vat_arithmetic(100_000.0, 200_000.0)
        assert result == "unknown"

    def test_zero_price_returns_unknown(self) -> None:
        """Zero or negative prices → 'unknown'."""
        assert _detect_via_vat_arithmetic(0.0, 123_000.0) == "unknown"
        assert _detect_via_vat_arithmetic(100_000.0, 0.0) == "unknown"
        assert _detect_via_vat_arithmetic(-10.0, 123_000.0) == "unknown"

    def test_within_2_pln_tolerance(self) -> None:
        """VAT ratio match within ±2 PLN tolerance."""
        # 100_000 × 1.23 = 123_000. Off by 1.5 PLN → still match
        result = _detect_via_vat_arithmetic(100_000.0, 123_001.5)
        assert result == "netto"


# ═══════════════════════════════════════════════════════════════════
# Domain propagation to paid_options
# ═══════════════════════════════════════════════════════════════════


class TestDomainPropagation:
    """_propagate_domain_to_options() behavior."""

    def test_unknown_options_get_domain(self) -> None:
        """Options with 'unknown' price_type → set to detected domain."""
        card = {
            "paid_options": [
                {"name": "Hak", "price": "5 000 PLN", "price_type": "unknown"},
            ],
        }
        _propagate_domain_to_options(card, "netto")
        assert card["paid_options"][0]["price_type"] == "netto"

    def test_explicit_option_type_preserved(self) -> None:
        """Options with explicit price_type in price string → keep it."""
        card = {
            "paid_options": [
                {
                    "name": "Hak",
                    "price": "5 000 PLN brutto",
                    "price_type": "unknown",
                },
            ],
        }
        _propagate_domain_to_options(card, "netto")
        # Price string says brutto → should override to brutto
        assert card["paid_options"][0]["price_type"] == "brutto"

    def test_unknown_domain_does_not_propagate(self) -> None:
        """If domain is 'unknown', options are left unchanged."""
        card = {
            "paid_options": [
                {"name": "Hak", "price": "5 000 PLN", "price_type": "unknown"},
            ],
        }
        _propagate_domain_to_options(card, "unknown")
        assert card["paid_options"][0]["price_type"] == "unknown"

    def test_non_dict_option_skipped(self) -> None:
        """Non-dict items in paid_options → skip gracefully."""
        card: dict = {
            "paid_options": ["not a dict", None],
        }
        _propagate_domain_to_options(card, "netto")
        # Should not crash


# ═══════════════════════════════════════════════════════════════════
# Report serialization
# ═══════════════════════════════════════════════════════════════════


class TestValidationReportSerialization:
    """ValidationReport and ValidationWarning .to_dict()."""

    def test_empty_report_serialization(self) -> None:
        report = ValidationReport()
        d = report.to_dict()
        assert d["is_valid"] is True
        assert d["warnings"] == []
        assert d["parsed_prices"]["base"] is None

    def test_warning_serialization_includes_optional_fields(self) -> None:
        w = ValidationWarning(
            rule="TEST_RULE",
            message="test message",
            severity="WARNING",
            expected=100.0,
            actual=110.0,
            diff_pct=10.12345,
        )
        d = w.to_dict()
        assert d["rule"] == "TEST_RULE"
        assert d["expected"] == 100.0
        assert d["actual"] == 110.0
        assert d["diff_pct"] == 10.12  # rounded to 2 decimal places

    def test_warning_without_optional_fields(self) -> None:
        w = ValidationWarning(
            rule="TEST_RULE",
            message="test",
            severity="INFO",
        )
        d = w.to_dict()
        assert "expected" not in d
        assert "actual" not in d
        assert "diff_pct" not in d

    def test_error_severity_sets_invalid(self) -> None:
        report = ValidationReport()
        assert report.is_valid is True
        report.add(
            ValidationWarning(
                rule="TEST",
                message="critical issue",
                severity="ERROR",
            )
        )
        assert report.is_valid is False

    def test_warning_severity_keeps_valid(self) -> None:
        report = ValidationReport()
        report.add(
            ValidationWarning(
                rule="TEST",
                message="minor issue",
                severity="WARNING",
            )
        )
        assert report.is_valid is True
        assert len(report.warnings) == 1


# ═══════════════════════════════════════════════════════════════════
# Pipeline integration
# ═══════════════════════════════════════════════════════════════════


class TestPipelineIntegration:
    """validate_and_flag_prices() integration."""

    def test_injects_validation_into_card_summary(self) -> None:
        pro_data = {
            "card_summary": {
                "base_price": "180 000 PLN brutto",
                "options_price": "20 000 PLN brutto",
                "total_price": "200 000 PLN brutto",
            },
        }
        result = validate_and_flag_prices(pro_data)
        validation = result["card_summary"]["_validation"]
        assert validation["is_valid"] is True
        assert isinstance(validation["warnings"], list)

    def test_handles_missing_card_summary(self) -> None:
        pro_data = {"digital_twin": {}}
        result = validate_and_flag_prices(pro_data)
        assert "_validation" not in result.get("card_summary", {})

    def test_unknown_brand_survives(self) -> None:
        """MarkaX — bulletproof: no crash for unknown brand."""
        pro_data = {
            "card_summary": {
                "base_price": "99 000 PLN brutto",
                "total_price": "99 000 PLN brutto",
                "paid_options": [],
            },
        }
        result = validate_and_flag_prices(pro_data)
        assert result["card_summary"]["_validation"]["is_valid"] is True

    def test_injects_price_domain(self) -> None:
        """Pipeline should inject _price_domain into card_summary."""
        pro_data = {
            "card_summary": {
                "base_price": "150 000 PLN netto",
                "total_price": "184 500 PLN brutto",
            },
        }
        result = validate_and_flag_prices(pro_data)
        assert result["card_summary"]["_price_domain"] == "netto"

    def test_empty_card_summary_dict(self) -> None:
        """Empty card_summary dict {} now gets validation flags (fix #V3)."""
        pro_data: dict = {"card_summary": {}}
        result = validate_and_flag_prices(pro_data)
        # Empty dict is now validated — should get _validation with is_valid=False (due to unknown domain)
        assert "_validation" in result["card_summary"]
        assert result["card_summary"]["_validation"]["is_valid"] is False


# ═══════════════════════════════════════════════════════════════════
# Real-world scenarios
# ═══════════════════════════════════════════════════════════════════


class TestRealWorldScenarios:
    """Realistic vehicle card data."""

    def test_toyota_corolla_valid(self) -> None:
        """Standard fleet car — everything matches."""
        card = {
            "base_price": "98 900 PLN netto",
            "options_price": "8 500 PLN netto",
            "total_price": "107 400 PLN netto",
            "paid_options": [
                {"name": "Nawigacja", "price": "3 500 PLN"},
                {"name": "Czujniki parkowania", "price": "2 500 PLN"},
                {"name": "Kamera cofania", "price": "2 500 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is True
        assert len(report.warnings) == 0

    def test_bmw_x5_with_expensive_option(self) -> None:
        """Premium car with very expensive factory option — gets flagged."""
        card = {
            "base_price": "350 000 PLN netto",
            "options_price": "200 000 PLN netto",
            "total_price": "550 000 PLN netto",
            "paid_options": [
                {"name": "Pakiet M Sport", "price": "180 000 PLN"},
                {"name": "Skóra Merino", "price": "20 000 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        # 180k / 350k = 51.4% > 50% → flagged
        expensive = [
            w
            for w in report.warnings
            if w.rule == "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE"
        ]
        assert len(expensive) == 1

    def test_marka_x_unknown_brand_no_crash(self) -> None:
        """Completely unknown brand in realistic scenario — bulletproof."""
        card = {
            "base_price": "120 000 PLN brutto",
            "options_price": "5 000 PLN brutto",
            "total_price": "125 000 PLN brutto",
            "paid_options": [
                {"name": "Nieznana opcja", "price": "5 000 PLN"},
            ],
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is True
        assert len(report.warnings) == 0


# ═══════════════════════════════════════════════════════════════════
# Rule 8: Power consistency
# ═══════════════════════════════════════════════════════════════════


class TestPowerConsistency:
    """Rule: power_kw * 1.36 ≈ power_hp."""

    def test_power_consistent(self) -> None:
        """110 kW * 1.36 = 149.6 ≈ 150 KM."""
        card = {
            "power_kw": 110,
            "power_hp": 150,
            "base_price": "100 000 PLN brutto",
            "total_price": "100 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        warnings = [w for w in report.warnings if w.rule == "POWER_KW_HP_MISMATCH"]
        assert len(warnings) == 0

    def test_power_mismatch(self) -> None:
        """110 kW * 1.36 != 130 KM."""
        card = {
            "power_kw": 110,
            "power_hp": 130,
            "base_price": "100 000 PLN brutto",
            "total_price": "100 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        warnings = [w for w in report.warnings if w.rule == "POWER_KW_HP_MISMATCH"]
        assert len(warnings) == 1
        assert warnings[0].expected == 150

    def test_power_missing(self) -> None:
        """If power is missing, no warning."""
        card = {
            "power_kw": None,
            "power_hp": 150,
            "base_price": "100 000 PLN brutto",
            "total_price": "100 000 PLN brutto",
        }
        report = validate_card_summary_prices(card)
        warnings = [w for w in report.warnings if w.rule == "POWER_KW_HP_MISMATCH"]
        assert len(warnings) == 0

    def test_hallucinated_prices_all_rules_fire(self) -> None:
        """Worst-case AI hallucination — multiple rules trigger."""
        card = {
            "base_price": "500 000 PLN brutto",
            "options_price": "100 000 PLN brutto",
            "total_price": "200 000 PLN brutto",  # 600k vs 200k — huge gap
            "paid_options": [
                {"name": "Zabudowa", "price": "300 000 PLN"},  # 60% of base
            ],
        }
        report = validate_card_summary_prices(card)
        assert report.is_valid is False
        rules_fired = {w.rule for w in report.warnings}
        assert "BASE_PLUS_OPTIONS_VS_TOTAL" in rules_fired
        assert "TOTAL_BELOW_BASE" in rules_fired
        assert "SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE" in rules_fired
        assert "OPTIONS_SUM_MISMATCH" in rules_fired


# ═══════════════════════════════════════════════════════════════════
# Auto-promote base_price from digital_twin.pricing when missing in
# card_summary. Triggered by Audi configurator PDFs which omit
# netto/brutto suffix — CARD_SUMMARY_PROMPT then leaves card_summary
# prices null, but the digital twin extractor still catches them.
# ═══════════════════════════════════════════════════════════════════


class TestPromoteBasePriceFromDigitalTwin:
    def _audi_pro_data(self) -> dict:
        # Real shape from GOA-25-381231 (AUDI A6) — base_price extracted by
        # Gemini Pro into digital_twin.pricing, but absent in card_summary.
        return {
            "brand": "Audi",
            "model": "A6",
            "card_summary": {"base_price": None, "total_price": None, "options_price": None},
            "digital_twin": {
                "pricing": {
                    "base_price": "241 000 PLN",
                    "total_price": "218 819 PLN",
                    "options_price": "46 920 PLN",
                }
            },
        }

    def test_promotes_when_card_summary_empty(self) -> None:
        result = validate_and_flag_prices(self._audi_pro_data())
        cs = result["card_summary"]
        assert cs["base_price"] == "241 000 PLN brutto"
        assert cs["total_price"] == "218 819 PLN brutto"
        assert cs["options_price"] == "46 920 PLN brutto"

    def test_validation_succeeds_after_promote(self) -> None:
        result = validate_and_flag_prices(self._audi_pro_data())
        cs = result["card_summary"]
        # After promotion the validator should parse base/total/options correctly
        assert cs["_price_domain"] == "brutto"
        parsed = cs["_validation"]["parsed_prices"]
        assert parsed["base"] == 241000.0
        assert parsed["total"] == 218819.0
        assert parsed["options"] == 46920.0
        # PRICE_DOMAIN_UNKNOWN warning should NOT fire after promotion
        rules = {w["rule"] for w in cs["_validation"]["warnings"]}
        assert "PRICE_DOMAIN_UNKNOWN" not in rules

    def test_does_not_overwrite_existing_card_summary_prices(self) -> None:
        data = self._audi_pro_data()
        data["card_summary"]["base_price"] = "200 000 PLN netto"  # already set
        result = validate_and_flag_prices(data)
        # Existing card_summary value wins
        assert result["card_summary"]["base_price"] == "200 000 PLN netto"

    def test_preserves_existing_domain_suffix_in_digital_twin(self) -> None:
        data = self._audi_pro_data()
        data["digital_twin"]["pricing"]["base_price"] = "241 000 PLN netto"
        result = validate_and_flag_prices(data)
        # If digital_twin string already declared netto, don't blindly append " brutto"
        assert result["card_summary"]["base_price"] == "241 000 PLN netto"

    def test_no_digital_twin_pricing_is_safe(self) -> None:
        # Skoda-shape: card_summary already has prices, no digital_twin section
        data = {
            "card_summary": {
                "base_price": "143500 PLN brutto",
                "options_price": "0 PLN brutto",
                "total_price": "143500 PLN brutto",
            }
        }
        result = validate_and_flag_prices(data)
        assert result["card_summary"]["base_price"] == "143500 PLN brutto"


# ═══════════════════════════════════════════════════════════════════
# Rule 14: FULL_SUM_INTEGRITY — total = base + paid_options + service_equipment
# Memory: extractor_price_quirks (Renault Master 2026-05-19)
# ═══════════════════════════════════════════════════════════════════


class TestFullSumIntegrity:
    """AI sometimes returns `total_price` that excludes `service_equipment`
    (zabudowa, agregat). Rule 14 catches this against the field-by-field sum.
    """

    def _renault_master_shape(self, total_price: str) -> dict:
        """Dual-component service_equipment shape from Renault Master case."""
        return {
            "base_price": "167218.50 PLN brutto",
            "total_price": total_price,
            "options_price": None,  # AUTO_FIX may rewrite
            "_price_domain": "brutto",
            "paid_options": [
                {"name": "Pakiet Conversion 2", "price": "738.00 PLN brutto", "category": "Fabryczna"},
                {"name": "światła przeciwmgłowe", "price": "738.00 PLN brutto", "category": "Fabryczna"},
                {"name": "asystent świateł", "price": "553.50 PLN brutto", "category": "Fabryczna"},
            ],
            "service_equipment": {
                "name": "Agregat + Zabudowa",
                "total_price_net": "69510.00 PLN netto",
                "total_price_gross": "85497.30 PLN brutto",
                "components": [
                    {
                        "name": "Agregat Zanotti Z380",
                        "price_net": "30510.00 PLN netto",
                        "price_gross": "37527.30 PLN brutto",
                    },
                    {
                        "name": "Zabudowa Kontener Izotermiczny",
                        "price_net": "39000.00 PLN netto",
                        "price_gross": "47970.00 PLN brutto",
                    },
                ],
            },
        }

    def test_total_excludes_service_equipment_triggers_error(self) -> None:
        """Realny case: Gemini zwrócił total=204 817 (cena pojazdu, bez
        zabudowy). Pełna suma powinna być 254 745 (= 167 218 + 2 030 + 85 497).
        FULL_SUM_INTEGRITY musi to wykryć i zwrócić ERROR."""
        card = self._renault_master_shape("204817.14 PLN brutto")
        report = validate_card_summary_prices(card)

        flagged = [w for w in report.warnings if w.rule == "FULL_SUM_INTEGRITY"]
        assert len(flagged) == 1
        assert flagged[0].severity == "ERROR"
        # Spodziewana suma: 167218.50 + 2029.50 + 85497.30 = 254745.30
        assert flagged[0].expected is not None
        assert abs(flagged[0].expected - 254745.30) < 1.0
        assert abs(flagged[0].actual - 204817.14) < 0.01
        assert flagged[0].field_path == "total_price"

    def test_total_matches_field_sum_no_warning(self) -> None:
        """Healthy: total = base + paid + service → brak FULL_SUM_INTEGRITY."""
        card = self._renault_master_shape("254745.30 PLN brutto")
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "FULL_SUM_INTEGRITY"]
        assert flagged == []

    def test_unknown_domain_skips_rule(self) -> None:
        """Bez sufiksu netto/brutto w cenach i bez `_price_domain` — pasywnie
        pomijamy (PRICE_DOMAIN_UNKNOWN flaguje to osobno)."""
        card = self._renault_master_shape("204817.14 PLN brutto")
        # Strip netto/brutto suffix from all prices to defeat the inline inferer.
        card["base_price"] = "167218.50 PLN"
        card["total_price"] = "204817.14 PLN"
        card["_price_domain"] = "unknown"
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "FULL_SUM_INTEGRITY"]
        assert flagged == []

    def test_no_service_equipment_skips_rule(self) -> None:
        """Bez service_equipment i bez paid_options — Rule 2 wystarczy."""
        card = {
            "base_price": "100000 PLN brutto",
            "options_price": "20000 PLN brutto",
            "total_price": "120000 PLN brutto",
            "_price_domain": "brutto",
            "paid_options": [],
            "service_equipment": None,
        }
        report = validate_card_summary_prices(card)
        flagged = [w for w in report.warnings if w.rule == "FULL_SUM_INTEGRITY"]
        assert flagged == []

    def test_routes_to_hitl_via_validate_and_flag(self) -> None:
        """End-to-end: Renault Master shape przez `validate_and_flag_prices`
        kończy z `is_valid=False` co kieruje pojazd do `needs_review`."""
        card = self._renault_master_shape("204817.14 PLN brutto")
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]
        rules = [w["rule"] for w in cs["_validation"]["warnings"]]
        assert "FULL_SUM_INTEGRITY" in rules
        assert cs["_validation"]["is_valid"] is False


# ═══════════════════════════════════════════════════════════════════
# AUTO_FIX guard: service_equipment included in derivation equation
# ═══════════════════════════════════════════════════════════════════


class TestAutoFixWithServiceEquipment:
    """Per memory `extractor_price_quirks` (2026-05-19) — AUTO_FIX
    options-derivation musi uwzględniać `service_equipment.total` w równaniu,
    inaczej regeneruje fałszywe options_price które pasują do niepełnego total.
    """

    def test_auto_fix_subtracts_service_equipment(self) -> None:
        """Gdy total ZAWIERA service_equipment, AUTO_FIX powinno wyliczyć
        options_price = total - service_total - base (rabat=0).

        Setup: base=167218.50, total=254745.30 (= base + 2030 paid + 85497 service).
        Oczekiwane: options_price ≈ 2030 (= 254745 - 85497 - 167218)."""
        card = {
            "base_price": "167218.50 PLN brutto",
            "options_price": "999999 PLN brutto",  # zła wartość — wymusza BASE_PLUS_OPTIONS_VS_TOTAL
            "total_price": "254745.30 PLN brutto",
            "service_equipment": {
                "name": "Zabudowa + Agregat",
                "total_price_gross": "85497.30 PLN brutto",
                "total_price_net": "69510.00 PLN netto",
                "components": [],
            },
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]
        # 254745 - 85497 - 167218 = 2030
        opts = str(cs.get("options_price", ""))
        assert "2029" in opts or "2030" in opts, f"got: {opts}"

    def test_auto_fix_skipped_when_negative(self) -> None:
        """Gdy service_total odjęty od total daje ujemną pulę opcji,
        AUTO_FIX powinien się wstrzymać (a FULL_SUM_INTEGRITY flagować w HITL).

        Renault Master shape: total=204817 (cena pojazdu bez service_equipment).
        204817 - 85497 - 167218 = -47898 < 0 → AUTO_FIX wstrzymany.
        """
        card = {
            "base_price": "167218.50 PLN brutto",
            "options_price": "Brak",
            "total_price": "204817.14 PLN brutto",
            "service_equipment": {
                "name": "Zabudowa + Agregat",
                "total_price_gross": "85497.30 PLN brutto",
                "total_price_net": "69510.00 PLN netto",
                "components": [],
            },
        }
        result = validate_and_flag_prices({"card_summary": card})
        cs = result["card_summary"]
        rules = [w["rule"] for w in cs["_validation"]["warnings"]]
        assert "AUTO_FIX_APPLIED" not in rules
        # Hard validator powinien wziąć tę sprawę
        assert "FULL_SUM_INTEGRITY" in rules
