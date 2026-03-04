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
        """Bazowy scenariusz: WP=100k, WR=50k, 36mc."""
        inp = AmortyzacjaInput(wp=100_000.0, wr=50_000.0, okres=36)
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.utrata_wartosci == pytest.approx(50_000.0)
        assert result.kwota_amortyzacji_1_miesiac == pytest.approx(
            50_000.0 / 36, rel=1e-6
        )
        expected_pct = (50_000.0 / 36) / 100_000.0
        assert result.amortyzacja_procent == pytest.approx(expected_pct, rel=1e-6)

    def test_zero_okres(self) -> None:
        """Edge-case: okres = 0 nie crashuje."""
        inp = AmortyzacjaInput(wp=100_000.0, wr=50_000.0, okres=0)
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.amortyzacja_procent == 0.0

    def test_zero_wp(self) -> None:
        """Edge-case: WP = 0 (brak ceny zakupu)."""
        inp = AmortyzacjaInput(wp=0.0, wr=0.0, okres=36)
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.amortyzacja_procent == 0.0

    def test_wr_equals_wp(self) -> None:
        """WR = WP -> zero amortyzacji."""
        inp = AmortyzacjaInput(wp=80_000.0, wr=80_000.0, okres=48)
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.utrata_wartosci == 0.0
        assert result.amortyzacja_procent == 0.0

    def test_wr_greater_than_wp(self) -> None:
        """WR > WP -> ujemna amortyzacja (samochód zyskujący na wartości)."""
        inp = AmortyzacjaInput(wp=80_000.0, wr=90_000.0, okres=48)
        result = AmortyzacjaCalculator(inp).calculate()

        assert result.utrata_wartosci < 0.0
        assert result.amortyzacja_procent < 0.0

    def test_long_period(self) -> None:
        """Długi okres – 84 miesiące."""
        inp = AmortyzacjaInput(wp=150_000.0, wr=30_000.0, okres=84)
        result = AmortyzacjaCalculator(inp).calculate()

        expected_utrata = 120_000.0
        assert result.utrata_wartosci == pytest.approx(expected_utrata)
        expected_pct = (120_000.0 / 84) / 150_000.0
        assert result.amortyzacja_procent == pytest.approx(expected_pct, rel=1e-6)

    def test_result_type(self) -> None:
        """Sprawdza typ wyniku."""
        inp = AmortyzacjaInput(wp=100_000.0, wr=50_000.0, okres=36)
        result = AmortyzacjaCalculator(inp).calculate()

        assert isinstance(result, AmortyzacjaResult)
