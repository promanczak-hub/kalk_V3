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
        # Empty dict is now validated — should get _validation with is_valid=True
        assert "_validation" in result["card_summary"]
        assert result["card_summary"]["_validation"]["is_valid"] is True


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
