"""Testy sub-kalkulatora stawki (V1 parity)."""

import pytest

from core.LTRSubCalculatorStawka import (
    KosztItem,
    StawkaCalculator,
    StawkaInput,
    StawkaResult,
)


def _make_input(
    marza: float = 0.08,
    czynsz_inicjalny: float = 0.0,
    okres: int = 36,
    **overrides: float,
) -> StawkaInput:
    """Fabryka inputu z rozsądnymi domyślnymi."""
    defaults = {
        "koszt_mc": 2_000.0,
        "koszt_mc_bez_czynszu": 2_200.0,
        "utrata_wartosci_netto": 40_000.0,
        "koszty_finansowe_netto": 5_000.0,
        "ubezpieczenie_netto": 8_000.0,
        "samochod_zastepczy_netto": 3_000.0,
        "koszty_dodatkowe_netto": 2_000.0,
        "opony_netto": 4_000.0,
        "serwis_netto": 6_000.0,
        "okres": okres,
        "marza": marza,
        "czynsz_inicjalny": czynsz_inicjalny,
    }
    defaults.update(overrides)  # type: ignore[arg-type]
    return StawkaInput(**defaults)  # type: ignore[arg-type]


class TestStawkaCalculator:
    """Testy StawkaCalculator."""

    def test_basic_calculation_no_upfront(self) -> None:
        """Bazowy scenariusz: brak czynszu inicjalnego -> podstawa = koszt_mc."""
        inp = _make_input(marza=0.08, czynsz_inicjalny=0.0)
        result = StawkaCalculator(inp).calculate()

        # podstawaMarzy = koszt_mc = 2000
        assert result.podstawa_marzy == pytest.approx(2_000.0)
        # marzaMC = 2000 * (1/(1-0.08)) - 2000 = 2000 * 1.08696 - 2000 = 173.91
        expected_marza_mc = 2_000.0 * (1.0 / (1.0 - 0.08)) - 2_000.0
        assert result.marza_mc == pytest.approx(expected_marza_mc, rel=1e-4)

    def test_basic_with_upfront(self) -> None:
        """Z czynszem inicjalnym: podstawa = koszt_mc_bez_czynszu."""
        inp = _make_input(marza=0.08, czynsz_inicjalny=10_000.0)
        result = StawkaCalculator(inp).calculate()

        assert result.podstawa_marzy == pytest.approx(2_200.0)

    def test_oferowana_stawka_positive(self) -> None:
        """Oferowana stawka > 0 przy typowych danych."""
        inp = _make_input()
        result = StawkaCalculator(inp).calculate()

        assert result.oferowana_stawka > 0.0
        assert result.czynsz_finansowy > 0.0
        assert result.czynsz_techniczny > 0.0

    def test_stawka_equals_cf_plus_ct(self) -> None:
        """oferowana_stawka = czynsz_finansowy + czynsz_techniczny."""
        inp = _make_input()
        result = StawkaCalculator(inp).calculate()

        assert result.oferowana_stawka == pytest.approx(
            result.czynsz_finansowy + result.czynsz_techniczny, rel=1e-6
        )

    def test_przychod_equals_stawka_times_okres(self) -> None:
        """przychód = oferowana_stawka * okres."""
        inp = _make_input(okres=48)
        result = StawkaCalculator(inp).calculate()

        assert result.przychod == pytest.approx(result.oferowana_stawka * 48, rel=1e-6)

    def test_marza_100_percent_raises(self) -> None:
        """Marża = 100% -> ValueError (dzielenie przez zero)."""
        inp = _make_input(marza=1.0)
        with pytest.raises(ValueError, match="1 - marza = 0"):
            StawkaCalculator(inp).calculate()

    def test_zero_okres(self) -> None:
        """Okres = 0 -> bezpieczny pusty wynik."""
        inp = _make_input(okres=0)
        result = StawkaCalculator(inp).calculate()

        assert result.oferowana_stawka == 0.0

    def test_zero_marza(self) -> None:
        """Marża = 0% -> brak narzutu, stawka = baza."""
        inp = _make_input(marza=0.0)
        result = StawkaCalculator(inp).calculate()

        assert result.marza_mc == pytest.approx(0.0)
        # Stawka = suma baz (koszt MC per składnik)
        assert result.oferowana_stawka > 0.0

    def test_manual_margin_override(self) -> None:
        """Korekty ręczne podziału marży."""
        inp = _make_input()
        inp.marza_koszt_finansowy_pct = 0.5  # 50% marży na koszty fin.
        inp.marza_ubezpieczenie_pct = 0.2
        inp.marza_samochod_zastepczy_pct = 0.1
        inp.marza_serwis_pct = 0.1
        inp.marza_opony_pct = 0.05
        inp.marza_koszty_dodatkowe_pct = 0.05

        result = StawkaCalculator(inp).calculate()

        # Korekty powinny dać inne wartości niż auto
        assert result.koszt_finansowy.rozklad_marzy_korekta == pytest.approx(0.5)
        assert result.koszt_ubezpieczenie.rozklad_marzy_korekta == pytest.approx(0.2)

    def test_all_six_components_present(self) -> None:
        """Sprawdza, że wszystkich 6 składników kosztowych jest w wyniku."""
        inp = _make_input()
        result = StawkaCalculator(inp).calculate()

        assert isinstance(result.koszt_finansowy, KosztItem)
        assert isinstance(result.koszt_ubezpieczenie, KosztItem)
        assert isinstance(result.koszt_samochod_zastepczy, KosztItem)
        assert isinstance(result.koszt_serwis, KosztItem)
        assert isinstance(result.koszt_opony, KosztItem)
        assert isinstance(result.koszt_admin, KosztItem)

    def test_result_type(self) -> None:
        """Sprawdza typ wyniku."""
        inp = _make_input()
        result = StawkaCalculator(inp).calculate()

        assert isinstance(result, StawkaResult)

    def test_margin_distribution_sums_to_one(self) -> None:
        """Auto-rozkład marży: suma wag = 1.0."""
        inp = _make_input()
        result = StawkaCalculator(inp).calculate()

        total_weights = (
            result.koszt_finansowy.rozklad_marzy
            + result.koszt_ubezpieczenie.rozklad_marzy
            + result.koszt_samochod_zastepczy.rozklad_marzy
            + result.koszt_serwis.rozklad_marzy
            + result.koszt_opony.rozklad_marzy
            + result.koszt_admin.rozklad_marzy
        )
        assert total_weights == pytest.approx(1.0, rel=1e-4)
