"""Tests for core.pipeline_price_validator — financial consistency checks."""

from core.pipeline_price_validator import (
    validate_card_summary_prices,
    validate_and_flag_prices,
)


class TestSumConsistency:
    """Rule: base + options ≈ total."""

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
            "total_price": "190 000 PLN brutto",  # 180k + 25k = 205k ≠ 190k (7.3%)
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
            "total_price": "220 400 PLN brutto",  # 220k vs 220.4k = 0.18% < 0.2%
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


class TestSanityChecks:
    """Rule: prices must be in realistic range."""

    def test_suspiciously_low_price(self) -> None:
        card = {
            "base_price": "3 000 PLN brutto",
            "total_price": "3 000 PLN brutto",
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
