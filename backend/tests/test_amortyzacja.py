"""Testy sub-kalkulatora amortyzacji (V1 parity)."""

import pytest

from core.LTRSubCalculatorAmortyzacja import (
    AmortyzacjaCalculator,
    AmortyzacjaInput,
    AmortyzacjaResult,
)


class TestAmortyzacjaCalculator:
    """Testy AmortyzacjaCalculator."""

    def test_basic_calculation(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=100_000.0, wp_amortyzacja=100_000.0, wr=50_000.0, okres=36
        )
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.utrata_wartosci == pytest.approx(50_000.0)
        assert result.kwota_amortyzacji_1_miesiac == pytest.approx(
            50_000.0 / 36, rel=1e-6
        )
        expected_pct = (50_000.0 / 36) / 100_000.0
        assert result.amortyzacja_procent == pytest.approx(expected_pct, rel=1e-6)

    def test_zero_okres(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=100_000.0, wp_amortyzacja=100_000.0, wr=50_000.0, okres=0
        )
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.amortyzacja_procent == 0.0

    def test_zero_wp(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=0.0, wp_amortyzacja=0.0, wr=0.0, okres=36
        )
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.amortyzacja_procent == 0.0

    def test_wr_equals_wp(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=80_000.0, wp_amortyzacja=80_000.0, wr=80_000.0, okres=48
        )
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.utrata_wartosci == 0.0
        assert result.amortyzacja_procent == 0.0

    def test_wr_greater_than_wp(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=80_000.0, wp_amortyzacja=80_000.0, wr=90_000.0, okres=48
        )
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.utrata_wartosci < 0.0
        assert result.amortyzacja_procent < 0.0

    def test_long_period(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=150_000.0, wp_amortyzacja=150_000.0, wr=30_000.0, okres=84
        )
        result = AmortyzacjaCalculator(inp).calculate()

        expected_utrata = 120_000.0
        assert result.utrata_wartosci == pytest.approx(expected_utrata)
        expected_pct = (120_000.0 / 84) / 150_000.0
        assert result.amortyzacja_procent == pytest.approx(expected_pct, rel=1e-6)

    def test_result_type(self) -> None:
        inp = AmortyzacjaInput(
            wp_finansowanie=100_000.0, wp_amortyzacja=100_000.0, wr=50_000.0, okres=36
        )
        result = AmortyzacjaCalculator(inp).calculate()

        assert isinstance(result, AmortyzacjaResult)
