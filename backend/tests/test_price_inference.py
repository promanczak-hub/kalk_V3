"""Unit tests for core.price_inference — deterministic net/gross/VAT triangulation.

NO hardcoded VAT rate. NO Gemini. Pure logic.

Covers all permutations:
- all three (net + gross + vat) → verify consistency
- net + vat → compute gross
- gross + vat → compute net
- net + gross (no vat) → derive vat, validate against allowed rates
- single value + no vat → unknown domain
- conflict cases → flag VAT_TRIANGULATION_FAILED
- non-standard vat → flag VAT_RATE_NON_STANDARD
"""

from __future__ import annotations

import pytest

from core.price_inference import (
    PriceTriple,
    infer_price_pair,
)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _has_warning(triple: PriceTriple, rule: str) -> bool:
    return any(w == rule for w in triple.warnings)


# ═══════════════════════════════════════════════════════════════════
# Group A: all three provided (net + gross + vat)
# ═══════════════════════════════════════════════════════════════════


class TestAllThreeProvided:
    def test_consistent_triple_no_warning(self) -> None:
        t = infer_price_pair(net=100_000.0, gross=123_000.0, vat_rate=0.23)
        assert t.net == 100_000.0
        assert t.gross == 123_000.0
        assert t.vat_rate == 0.23
        assert t.conversion_source == "explicit_both"
        assert t.warnings == []

    def test_inconsistent_triple_flags_triangulation_failed(self) -> None:
        # 100k * 1.23 = 123_000, ale dokument mówi 122_999 → diff ~8ppm < tolerance?
        # actually 1/123000 = ~8ppm, tolerance to 2‰ = 2000ppm → tu jeszcze OK
        # użyj większego konfliktu: 100k * 1.23 = 123_000 vs 122_500 (diff 0.4%)
        t = infer_price_pair(net=100_000.0, gross=122_500.0, vat_rate=0.23)
        assert _has_warning(t, "VAT_TRIANGULATION_FAILED")

    def test_within_tolerance_no_warning(self) -> None:
        # 100k * 1.23 = 123_000, vs 123_100 → diff 0.08% (under 2‰)
        t = infer_price_pair(net=100_000.0, gross=123_100.0, vat_rate=0.23)
        assert not _has_warning(t, "VAT_TRIANGULATION_FAILED")

    def test_non_standard_vat_flagged(self) -> None:
        # VAT 0.12 not in {0, 0.05, 0.08, 0.23} → WARNING but kept
        t = infer_price_pair(net=100_000.0, gross=112_000.0, vat_rate=0.12)
        assert _has_warning(t, "VAT_RATE_NON_STANDARD")
        # triangulation should still hold (100k * 1.12 = 112k)
        assert not _has_warning(t, "VAT_TRIANGULATION_FAILED")


# ═══════════════════════════════════════════════════════════════════
# Group B: net + vat → compute gross
# ═══════════════════════════════════════════════════════════════════


class TestNetPlusVatComputesGross:
    def test_standard_vat_23(self) -> None:
        t = infer_price_pair(net=100_000.0, gross=None, vat_rate=0.23)
        assert t.net == 100_000.0
        assert t.gross == 123_000.0
        assert t.vat_rate == 0.23
        assert t.conversion_source == "computed_from_net"
        assert t.warnings == []

    def test_vat_8_reduced(self) -> None:
        t = infer_price_pair(net=1_000.0, gross=None, vat_rate=0.08)
        assert t.gross == 1_080.0
        assert t.conversion_source == "computed_from_net"

    def test_vat_zero_export(self) -> None:
        t = infer_price_pair(net=100_000.0, gross=None, vat_rate=0.0)
        assert t.gross == 100_000.0
        assert t.conversion_source == "computed_from_net"
        assert not _has_warning(t, "VAT_RATE_NON_STANDARD")  # 0% is legal


# ═══════════════════════════════════════════════════════════════════
# Group C: gross + vat → compute net
# ═══════════════════════════════════════════════════════════════════


class TestGrossPlusVatComputesNet:
    def test_standard_vat(self) -> None:
        t = infer_price_pair(net=None, gross=123_000.0, vat_rate=0.23)
        assert t.net == 100_000.0
        assert t.gross == 123_000.0
        assert t.conversion_source == "computed_from_gross"

    def test_rounding_to_two_decimals(self) -> None:
        # 50_000 / 1.23 = 40650.40650...
        t = infer_price_pair(net=None, gross=50_000.0, vat_rate=0.23)
        assert t.net == 40_650.41


# ═══════════════════════════════════════════════════════════════════
# Group D: net + gross (no vat) → derive vat
# ═══════════════════════════════════════════════════════════════════


class TestNetPlusGrossDerivesVat:
    def test_derive_vat_23(self) -> None:
        t = infer_price_pair(net=100_000.0, gross=123_000.0, vat_rate=None)
        assert t.vat_rate == 0.23
        assert t.conversion_source == "explicit_both"
        assert not _has_warning(t, "VAT_RATE_NON_STANDARD")

    def test_derive_vat_8(self) -> None:
        t = infer_price_pair(net=1_000.0, gross=1_080.0, vat_rate=None)
        assert t.vat_rate == 0.08

    def test_derive_zero_vat(self) -> None:
        t = infer_price_pair(net=100_000.0, gross=100_000.0, vat_rate=None)
        assert t.vat_rate == 0.0

    def test_non_standard_derived_vat_flagged(self) -> None:
        # 100_000 → 115_000 → derived vat = 0.15 (not in standard set)
        t = infer_price_pair(net=100_000.0, gross=115_000.0, vat_rate=None)
        assert t.vat_rate == 0.15
        assert _has_warning(t, "VAT_RATE_NON_STANDARD")

    def test_within_tolerance_snaps_to_standard(self) -> None:
        # 100_000 → 123_050 → derived 0.2305, should snap to 0.23
        t = infer_price_pair(net=100_000.0, gross=123_050.0, vat_rate=None)
        assert t.vat_rate == 0.23
        assert not _has_warning(t, "VAT_RATE_NON_STANDARD")


# ═══════════════════════════════════════════════════════════════════
# Group E: single value, no VAT → unknown
# ═══════════════════════════════════════════════════════════════════


class TestSingleValueNoVat:
    def test_only_net_no_vat_unknown(self) -> None:
        t = infer_price_pair(net=100_000.0, gross=None, vat_rate=None)
        assert t.net == 100_000.0
        assert t.gross is None
        assert t.vat_rate is None
        assert t.conversion_source == "unknown"

    def test_only_gross_no_vat_unknown(self) -> None:
        t = infer_price_pair(net=None, gross=123_000.0, vat_rate=None)
        assert t.net is None
        assert t.gross == 123_000.0
        assert t.conversion_source == "unknown"

    def test_all_none_returns_empty(self) -> None:
        t = infer_price_pair(net=None, gross=None, vat_rate=None)
        assert t.net is None
        assert t.gross is None
        assert t.vat_rate is None


# ═══════════════════════════════════════════════════════════════════
# Group F: edge cases
# ═══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_negative_values_raise(self) -> None:
        with pytest.raises(ValueError):
            infer_price_pair(net=-100.0, gross=None, vat_rate=0.23)

    def test_negative_vat_raise(self) -> None:
        with pytest.raises(ValueError):
            infer_price_pair(net=100.0, gross=None, vat_rate=-0.1)

    def test_vat_above_one_raises(self) -> None:
        # VAT > 100% nie ma sensu
        with pytest.raises(ValueError):
            infer_price_pair(net=100.0, gross=None, vat_rate=1.5)

    def test_zero_net_gross_no_division_error(self) -> None:
        # Edge case: both zero, no VAT given — should not divide by zero
        t = infer_price_pair(net=0.0, gross=0.0, vat_rate=None)
        # 0/0 undefined → vat_rate stays None
        assert t.vat_rate is None
        assert t.net == 0.0
        assert t.gross == 0.0

    def test_explicit_zero_gross_with_positive_net_flags_conflict(self) -> None:
        # net=1000, gross=0, vat=0.23 → triangulation fails
        t = infer_price_pair(net=1_000.0, gross=0.0, vat_rate=0.23)
        assert _has_warning(t, "VAT_TRIANGULATION_FAILED")


# ═══════════════════════════════════════════════════════════════════
# Group G: custom allowed_vat_rates
# ═══════════════════════════════════════════════════════════════════


class TestCustomAllowedVatRates:
    def test_custom_rates_pass_through(self) -> None:
        # Allow only 0.19 (German VAT)
        t = infer_price_pair(
            net=100.0,
            gross=119.0,
            vat_rate=None,
            allowed_vat_rates=(0.0, 0.07, 0.19),
        )
        assert t.vat_rate == 0.19
        assert not _has_warning(t, "VAT_RATE_NON_STANDARD")

    def test_default_polish_rates_reject_german_vat(self) -> None:
        t = infer_price_pair(net=100.0, gross=119.0, vat_rate=0.19)
        assert _has_warning(t, "VAT_RATE_NON_STANDARD")


# ═══════════════════════════════════════════════════════════════════
# Group H: conversion_source contract
# ═══════════════════════════════════════════════════════════════════


class TestConversionSource:
    def test_explicit_both_when_both_provided(self) -> None:
        t = infer_price_pair(net=100.0, gross=123.0, vat_rate=0.23)
        assert t.conversion_source == "explicit_both"

    def test_computed_from_net_when_only_net(self) -> None:
        t = infer_price_pair(net=100.0, gross=None, vat_rate=0.23)
        assert t.conversion_source == "computed_from_net"

    def test_computed_from_gross_when_only_gross(self) -> None:
        t = infer_price_pair(net=None, gross=123.0, vat_rate=0.23)
        assert t.conversion_source == "computed_from_gross"

    def test_unknown_when_single_value_no_vat(self) -> None:
        t = infer_price_pair(net=100.0, gross=None, vat_rate=None)
        assert t.conversion_source == "unknown"
