"""Unit tests for the V3 validator rules in pipeline_validator_v3.

Rules:
- VAT_TRIANGULATION_FAILED   (ERROR)   — gross ≠ net × (1+vat) ±2‰
- VAT_RATE_NON_STANDARD      (WARNING) — vat ∉ {0, 0.05, 0.08, 0.23}
- CANONICAL_DUPLICATE_DETECTED (INFO)  — _duplicate_flags non-empty
- MULTI_VEHICLE_TWIN_INCOMPLETE (WARNING) — any twin missing base or low confidence
"""

from __future__ import annotations

from core.pipeline_price_validator import ValidationReport
from core.pipeline_validator_v3 import (
    check_canonical_duplicate,
    check_multi_vehicle_twin_completeness,
    check_vat_rate_standard,
    check_vat_triangulation,
)


def _new_report() -> ValidationReport:
    return ValidationReport()


# ═══════════════════════════════════════════════════════════════════
# VAT_TRIANGULATION_FAILED
# ═══════════════════════════════════════════════════════════════════


class TestVatTriangulation:
    def test_consistent_no_warning(self) -> None:
        card = {
            "base_price_net": 100_000.0,
            "base_price_gross": 123_000.0,
            "base_price_vat": 0.23,
        }
        r = _new_report()
        check_vat_triangulation(card, r)
        assert not any(w.rule == "VAT_TRIANGULATION_FAILED" for w in r.warnings)

    def test_inconsistent_triple_error(self) -> None:
        card = {
            "base_price_net": 100_000.0,
            "base_price_gross": 122_500.0,  # 0.4% off
            "base_price_vat": 0.23,
        }
        r = _new_report()
        check_vat_triangulation(card, r)
        failed = [w for w in r.warnings if w.rule == "VAT_TRIANGULATION_FAILED"]
        assert len(failed) == 1
        assert failed[0].severity == "ERROR"
        assert failed[0].field_path == "base_price"

    def test_multiple_groups_each_checked(self) -> None:
        card = {
            "base_price_net": 100.0, "base_price_gross": 123.0, "base_price_vat": 0.23,
            "options_price_net": 50.0, "options_price_gross": 70.0, "options_price_vat": 0.23,  # bad
            "total_price_net": 150.0, "total_price_gross": 184.5, "total_price_vat": 0.23,
        }
        r = _new_report()
        check_vat_triangulation(card, r)
        failed = [w for w in r.warnings if w.rule == "VAT_TRIANGULATION_FAILED"]
        assert len(failed) == 1
        assert failed[0].field_path == "options_price"

    def test_paid_options_checked(self) -> None:
        card = {
            "paid_options": [
                {
                    "name": "Pakiet zima",
                    "net_amount": 1000.0,
                    "gross_amount": 1100.0,  # vat 0.10, but declared 0.23
                    "vat_rate": 0.23,
                    "field_id": "po1",
                },
            ],
        }
        r = _new_report()
        check_vat_triangulation(card, r)
        failed = [w for w in r.warnings if w.rule == "VAT_TRIANGULATION_FAILED"]
        assert len(failed) == 1
        assert "paid_options" in failed[0].field_path

    def test_missing_data_skipped(self) -> None:
        # If we don't have all 3 values, can't triangulate — skip silently
        card = {"base_price_net": 100.0}
        r = _new_report()
        check_vat_triangulation(card, r)
        assert not any(w.rule == "VAT_TRIANGULATION_FAILED" for w in r.warnings)


# ═══════════════════════════════════════════════════════════════════
# VAT_RATE_NON_STANDARD
# ═══════════════════════════════════════════════════════════════════


class TestVatRateStandard:
    def test_standard_23_ok(self) -> None:
        r = _new_report()
        check_vat_rate_standard({"base_price_vat": 0.23}, r)
        assert not any(w.rule == "VAT_RATE_NON_STANDARD" for w in r.warnings)

    def test_zero_export_ok(self) -> None:
        r = _new_report()
        check_vat_rate_standard({"base_price_vat": 0.0}, r)
        assert not any(w.rule == "VAT_RATE_NON_STANDARD" for w in r.warnings)

    def test_eight_percent_ok(self) -> None:
        r = _new_report()
        check_vat_rate_standard({"base_price_vat": 0.08}, r)
        assert not any(w.rule == "VAT_RATE_NON_STANDARD" for w in r.warnings)

    def test_non_standard_warning(self) -> None:
        r = _new_report()
        check_vat_rate_standard({"base_price_vat": 0.15}, r)
        flagged = [w for w in r.warnings if w.rule == "VAT_RATE_NON_STANDARD"]
        assert len(flagged) == 1
        assert flagged[0].severity == "WARNING"

    def test_paid_option_with_nonstandard_vat(self) -> None:
        card = {
            "paid_options": [
                {"name": "X", "vat_rate": 0.17, "field_id": "po1"},
            ],
        }
        r = _new_report()
        check_vat_rate_standard(card, r)
        flagged = [w for w in r.warnings if w.rule == "VAT_RATE_NON_STANDARD"]
        assert len(flagged) == 1
        assert "paid_options" in flagged[0].field_path

    def test_none_vat_skipped(self) -> None:
        r = _new_report()
        check_vat_rate_standard({"base_price_vat": None}, r)
        assert not any(w.rule == "VAT_RATE_NON_STANDARD" for w in r.warnings)


# ═══════════════════════════════════════════════════════════════════
# CANONICAL_DUPLICATE_DETECTED
# ═══════════════════════════════════════════════════════════════════


class TestCanonicalDuplicate:
    def test_no_duplicates_no_warning(self) -> None:
        r = _new_report()
        check_canonical_duplicate({"_duplicate_flags": []}, r)
        assert not any(w.rule == "CANONICAL_DUPLICATE_DETECTED" for w in r.warnings)

    def test_missing_key_no_warning(self) -> None:
        r = _new_report()
        check_canonical_duplicate({}, r)
        assert not any(w.rule == "CANONICAL_DUPLICATE_DETECTED" for w in r.warnings)

    def test_with_duplicates_info_warning(self) -> None:
        card = {
            "_duplicate_flags": [
                {
                    "canonical_id": "abc123def456",
                    "field_ids": ["po1", "se_main"],
                    "names": ["Zabudowa", "Zabudowa"],
                },
            ],
        }
        r = _new_report()
        check_canonical_duplicate(card, r)
        flagged = [w for w in r.warnings if w.rule == "CANONICAL_DUPLICATE_DETECTED"]
        assert len(flagged) == 1
        assert flagged[0].severity == "INFO"
        # report stays valid — INFO doesn't fail
        assert r.is_valid

    def test_multiple_duplicate_groups(self) -> None:
        card = {
            "_duplicate_flags": [
                {"canonical_id": "a", "field_ids": ["1", "2"], "names": ["X", "X"]},
                {"canonical_id": "b", "field_ids": ["3", "4"], "names": ["Y", "Y"]},
            ],
        }
        r = _new_report()
        check_canonical_duplicate(card, r)
        flagged = [w for w in r.warnings if w.rule == "CANONICAL_DUPLICATE_DETECTED"]
        assert len(flagged) == 2


# ═══════════════════════════════════════════════════════════════════
# MULTI_VEHICLE_TWIN_INCOMPLETE
# ═══════════════════════════════════════════════════════════════════


class TestMultiVehicleTwinCompleteness:
    def test_all_complete_no_warning(self) -> None:
        twins = [
            {"base_price": "100000 PLN netto", "confidence_score": 0.95},
            {"base_price": "120000 PLN netto", "confidence_score": 0.92},
        ]
        warnings = check_multi_vehicle_twin_completeness(twins)
        assert warnings == []

    def test_one_missing_base_flagged(self) -> None:
        twins = [
            {"base_price": "100000 PLN netto", "confidence_score": 0.95},
            {"base_price": "Brak", "confidence_score": 0.95},
        ]
        warnings = check_multi_vehicle_twin_completeness(twins)
        assert len(warnings) == 1
        assert warnings[0].rule == "MULTI_VEHICLE_TWIN_INCOMPLETE"
        assert warnings[0].severity == "WARNING"
        assert "1" in warnings[0].field_path  # index of broken twin

    def test_low_confidence_flagged(self) -> None:
        twins = [
            {"base_price": "100000 PLN netto", "confidence_score": 0.95},
            {"base_price": "120000 PLN netto", "confidence_score": 0.3},
        ]
        warnings = check_multi_vehicle_twin_completeness(twins)
        assert len(warnings) == 1
        assert warnings[0].rule == "MULTI_VEHICLE_TWIN_INCOMPLETE"

    def test_single_vehicle_not_flagged(self) -> None:
        # Single twin = not multi-vehicle, skip
        twins = [{"base_price": "Brak", "confidence_score": 0.95}]
        warnings = check_multi_vehicle_twin_completeness(twins)
        assert warnings == []

    def test_empty_list_no_crash(self) -> None:
        assert check_multi_vehicle_twin_completeness([]) == []

    def test_none_input_no_crash(self) -> None:
        assert check_multi_vehicle_twin_completeness(None) == []
