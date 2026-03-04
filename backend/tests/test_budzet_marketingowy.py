"""Testy sub-kalkulatora budżetu marketingowego (V1 parity)."""

import pytest

from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
    BudzetMarketingowyResult,
)


class TestBudzetMarketingowyCalculator:
    """Testy BudzetMarketingowyCalculator."""

    def test_basic_calculation(self) -> None:
        """Bazowy scenariusz: WR=60k, VAT=1.23, budżet=2%."""
        inp = BudzetMarketingowyInput(
            wr_przewidywana_cena_sprzedazy=60_000.0,
            stawka_vat=1.23,
            budzet_marketingowy_ltr=0.02,
        )
        result = BudzetMarketingowyCalculator(inp).calculate()

        expected = 60_000.0 * 1.23 * 0.02
        assert result.korekta_wr_maks == pytest.approx(expected, rel=1e-6)

    def test_zero_wr(self) -> None:
        """WR = 0 -> brak korekty."""
        inp = BudzetMarketingowyInput(
            wr_przewidywana_cena_sprzedazy=0.0,
            stawka_vat=1.23,
            budzet_marketingowy_ltr=0.02,
        )
        result = BudzetMarketingowyCalculator(inp).calculate()

        assert result.korekta_wr_maks == 0.0

    def test_zero_budzet(self) -> None:
        """Budżet = 0 -> brak korekty."""
        inp = BudzetMarketingowyInput(
            wr_przewidywana_cena_sprzedazy=60_000.0,
            stawka_vat=1.23,
            budzet_marketingowy_ltr=0.0,
        )
        result = BudzetMarketingowyCalculator(inp).calculate()

        assert result.korekta_wr_maks == 0.0

    def test_high_wr(self) -> None:
        """Wysoka WR = 200k."""
        inp = BudzetMarketingowyInput(
            wr_przewidywana_cena_sprzedazy=200_000.0,
            stawka_vat=1.23,
            budzet_marketingowy_ltr=0.03,
        )
        result = BudzetMarketingowyCalculator(inp).calculate()

        expected = 200_000.0 * 1.23 * 0.03
        assert result.korekta_wr_maks == pytest.approx(expected, rel=1e-6)

    def test_result_type(self) -> None:
        """Sprawdza typ wyniku."""
        inp = BudzetMarketingowyInput(
            wr_przewidywana_cena_sprzedazy=60_000.0,
            stawka_vat=1.23,
            budzet_marketingowy_ltr=0.02,
        )
        result = BudzetMarketingowyCalculator(inp).calculate()

        assert isinstance(result, BudzetMarketingowyResult)
