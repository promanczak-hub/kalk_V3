"""Testy sub-kalkulatora kosztu dziennego (V1 parity)."""

import pytest

from core.LTRSubCalculatorKosztDzienny import (
    COEFF_KOSZT_DZIENNY,
    KosztDziennyCalculator,
    KosztDziennyInput,
    KosztDziennyResult,
)


def _make_input(
    utrata_z: float = 40_000.0,
    utrata_bez: float = 50_000.0,
    koszt_fin: float = 5_000.0,
    zastepczy: float = 3_000.0,
    dodatkowe: float = 2_000.0,
    ubezp: float = 8_000.0,
    opony: float = 4_000.0,
    serwis: float = 6_000.0,
    odsetki_bez: float = 7_000.0,
    okres: int = 36,
) -> KosztDziennyInput:
    return KosztDziennyInput(
        utrata_wartosci_z_czynszem=utrata_z,
        utrata_wartosci_bez_czynszu=utrata_bez,
        koszt_finansowy=koszt_fin,
        samochod_zastepczy_netto=zastepczy,
        koszty_dodatkowe_netto=dodatkowe,
        ubezpieczenie_netto=ubezp,
        opony_netto=opony,
        serwis_netto=serwis,
        suma_odsetek_bez_czynszu=odsetki_bez,
        okres=okres,
    )


class TestKosztDziennyCalculator:
    """Testy KosztDziennyCalculator."""

    def test_basic_calculation(self) -> None:
        """Bazowy scenariusz z typowymi wartościami."""
        inp = _make_input()
        result = KosztDziennyCalculator(inp).calculate()

        # Weryfikacja ręczna
        fin = 5_000.0 + 40_000.0  # 45000
        tech = 3_000.0 + 2_000.0 + 8_000.0 + 4_000.0 + 6_000.0  # 23000
        ogolem = fin + tech  # 68000
        mc = ogolem / 36
        dzienny = mc / COEFF_KOSZT_DZIENNY

        assert result.koszty_ogolem == pytest.approx(ogolem, rel=1e-6)
        assert result.koszt_mc == pytest.approx(mc, rel=1e-6)
        assert result.koszt_dzienny == pytest.approx(dzienny, rel=1e-6)

    def test_symulacja_bez_czynszu(self) -> None:
        """Weryfikacja symulacji BEZ czynszu inicjalnego."""
        inp = _make_input()
        result = KosztDziennyCalculator(inp).calculate()

        tech = 3_000.0 + 2_000.0 + 8_000.0 + 4_000.0 + 6_000.0  # 23000
        sym_fin = 50_000.0 + 7_000.0  # 57000
        sym_ogolem = sym_fin + tech  # 80000
        sym_mc = sym_ogolem / 36

        assert result.koszt_mc_bez_czynszu == pytest.approx(sym_mc, rel=1e-6)

    def test_zero_okres(self) -> None:
        """Okres = 0 -> bezpieczny zwrot zer."""
        inp = _make_input(okres=0)
        result = KosztDziennyCalculator(inp).calculate()

        assert result.koszt_dzienny == 0.0
        assert result.koszt_mc == 0.0

    def test_all_zeros(self) -> None:
        """Wszystkie koszty zerowe."""
        inp = _make_input(
            utrata_z=0.0,
            utrata_bez=0.0,
            koszt_fin=0.0,
            zastepczy=0.0,
            dodatkowe=0.0,
            ubezp=0.0,
            opony=0.0,
            serwis=0.0,
            odsetki_bez=0.0,
            okres=36,
        )
        result = KosztDziennyCalculator(inp).calculate()

        assert result.koszt_dzienny == 0.0
        assert result.koszty_ogolem == 0.0

    def test_result_type(self) -> None:
        """Sprawdza typ wyniku."""
        inp = _make_input()
        result = KosztDziennyCalculator(inp).calculate()

        assert isinstance(result, KosztDziennyResult)

    def test_daily_cost_coefficient(self) -> None:
        """Weryfikacja stałej V1: 30.4 dni/miesiąc."""
        assert COEFF_KOSZT_DZIENNY == 30.4
