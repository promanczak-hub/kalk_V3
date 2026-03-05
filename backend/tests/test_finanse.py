"""
TDD tests for LTRSubCalculatorFinanse — V1 parity.

V1 formuła PMT (PMT.cs L28):
    K = -kapitalDoSplaty
    im = oprocentowanie / 12
    imN = (1 + im) ^ n
    pmt = ((K * imN + W) * im) / (1 - imN)

V1 harmonogram (getRaty L138-188):
    for rata 1..n:
        RataOdsetkowa = KapitalDoSplaty * oprocentowanie / 12
        RataKapitalowa = Rata - RataOdsetkowa
        KapitalPoSplacie = KapitalDoSplaty - RataKapitalowa

V1 dwa warianty:
    zCzynszem: kredyt = WP - czynsz/VAT, wykup = min(kredyt, WR)
    bezCzynszu: kredyt = WP, wykup = ten sam co wyżej
"""

import pytest
import sys

sys.path.insert(0, "d:/kalk_v3/backend")

from core.LTRSubCalculatorFinanse import (  # noqa: E402
    FinanseInput,
    FinanseResult,
    FinanseCalculator,
    Rata,
)


# --- Scenariusz bazowy ---
# CAPEX netto = 100 000 PLN
# WR netto = 46 000 PLN
# Czynsz inicjalny brutto = 12 300 PLN (= 10 000 netto przy VAT 1.23)
# Okres = 48 mc
# WIBOR = 4.82%, Marża = 2.0% → oprocentowanie = 6.82%

BASE_INPUT = FinanseInput(
    WartoscPoczatkowaNetto=100_000.0,
    WrPrzewidywanaCenaSprzedazy=46_000.0,
    CzynszInicjalny=12_300.0,  # brutto
    CzynszProcent=0.0,
    RodzajCzynszu="Kwotowo",
    StawkaVAT=1.23,
    Okres=48,
    WIBORProcent=4.82,
    MarzaFinansowaProcent=2.0,
)


class TestFinanseInput:
    """Test poprawności danych wejściowych."""

    def test_czynsz_netto_kwotowy(self) -> None:
        """Czynsz kwotowy: brutto 12300 / 1.23 = 10 000 netto."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        assert abs(result.CzynszInicjalnyNetto - 10_000.0) < 0.01

    def test_czynsz_netto_procentowy(self) -> None:
        """Czynsz procentowy: 10% × CAPEX = 10 000 netto."""
        inp = FinanseInput(
            WartoscPoczatkowaNetto=100_000.0,
            WrPrzewidywanaCenaSprzedazy=46_000.0,
            CzynszInicjalny=0.0,
            CzynszProcent=10.0,
            RodzajCzynszu="Procentowo",
            StawkaVAT=1.23,
            Okres=48,
            WIBORProcent=4.82,
            MarzaFinansowaProcent=2.0,
        )
        calc = FinanseCalculator(inp)
        result = calc.calculate()
        assert abs(result.CzynszInicjalnyNetto - 10_000.0) < 0.01


class TestPMTFormula:
    """Test formuły PMT — identyczna z V1 PMT.cs."""

    def test_pmt_basic(self) -> None:
        """PMT dla kredytu 90k, wykup 46k, 48 rat, 6.82%."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        # PMT musi być > 0 (rata dodatnia)
        assert result.monthly_pmt_z_czynszem > 0
        # Rata < kredyt / okres (bo jest wykup)
        assert result.monthly_pmt_z_czynszem < 90_000 / 48

    def test_pmt_zero_rate(self) -> None:
        """Przy zerowym oprocentowaniu rata = (PV - FV) / n."""
        inp = FinanseInput(
            WartoscPoczatkowaNetto=100_000.0,
            WrPrzewidywanaCenaSprzedazy=46_000.0,
            CzynszInicjalny=0.0,
            CzynszProcent=0.0,
            RodzajCzynszu="Kwotowo",
            StawkaVAT=1.23,
            Okres=48,
            WIBORProcent=0.0,
            MarzaFinansowaProcent=0.0,
        )
        calc = FinanseCalculator(inp)
        result = calc.calculate()
        expected = (100_000.0 - 46_000.0) / 48
        assert abs(result.monthly_pmt_z_czynszem - expected) < 0.01
        assert abs(result.SumaOdsetekZczynszem) < 0.01


class TestDwaWarianty:
    """Test dwóch wariantów PMT — z czynszem i bez."""

    def test_suma_odsetek_rozne(self) -> None:
        """SumaOdsetekZczynszem ≠ SumaOdsetekBEZczynszu gdy czynsz > 0."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        # Z czynszem: mniejszy kredyt → mniej odsetek
        assert result.SumaOdsetekZczynszem < result.SumaOdsetekBEZczynszu

    def test_bez_czynszu_uzywa_pelny_capex(self) -> None:
        """Wariant bez czynszu liczy od pełnego WP."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        # Suma odsetek bez czynszu musi być > z czynszem
        assert result.SumaOdsetekBEZczynszu > result.SumaOdsetekZczynszem

    def test_wykup_identyczny_oba_warianty(self) -> None:
        """V1: wykup = min(kredyt_z_czynszem, WR) — ten sam dla obu."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        # Wykup = min(90000, 46000) = 46000
        assert abs(result.WykupKwota - 46_000.0) < 0.01

    def test_czynsz_zero_oba_identyczne(self) -> None:
        """Gdy czynsz = 0, oba warianty muszą dać identyczny wynik."""
        inp = FinanseInput(
            WartoscPoczatkowaNetto=100_000.0,
            WrPrzewidywanaCenaSprzedazy=46_000.0,
            CzynszInicjalny=0.0,
            CzynszProcent=0.0,
            RodzajCzynszu="Kwotowo",
            StawkaVAT=1.23,
            Okres=48,
            WIBORProcent=4.82,
            MarzaFinansowaProcent=2.0,
        )
        calc = FinanseCalculator(inp)
        result = calc.calculate()
        assert abs(result.SumaOdsetekZczynszem - result.SumaOdsetekBEZczynszu) < 0.01


class TestHarmonogram:
    """Test harmonogramu rat — pełne rozbicie 1..Okres."""

    def test_harmonogram_length(self) -> None:
        """Harmonogram z czynszem ma dokładnie Okres rat."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        assert len(result.RatyZczynszem) == 48

    def test_harmonogram_first_rate(self) -> None:
        """Pierwsza rata: KapitalDoSplaty = wartoscKredytu."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        first = result.RatyZczynszem[0]
        assert first.NumerRaty == 1
        assert abs(first.KapitalDoSplaty - 90_000.0) < 0.01

    def test_harmonogram_suma_odsetek(self) -> None:
        """Suma rat odsetkowych = SumaOdsetekZczynszem."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        suma = sum(r.RataOdsetkowa for r in result.RatyZczynszem)
        assert abs(suma - result.SumaOdsetekZczynszem) < 0.01

    def test_harmonogram_kapital_splacony(self) -> None:
        """Po ostatniej racie KapitalPoSplacie ≈ WykupKwota."""
        calc = FinanseCalculator(BASE_INPUT)
        result = calc.calculate()
        last = result.RatyZczynszem[-1]
        assert abs(last.KapitalPoSplacie - result.WykupKwota) < 1.0


class TestEdgeCases:
    """Testy krawędziowe — pancerne funkcje."""

    def test_okres_zero(self) -> None:
        """Okres = 0 → zerowy wynik."""
        inp = FinanseInput(
            WartoscPoczatkowaNetto=100_000.0,
            WrPrzewidywanaCenaSprzedazy=46_000.0,
            CzynszInicjalny=0.0,
            CzynszProcent=0.0,
            RodzajCzynszu="Kwotowo",
            StawkaVAT=1.23,
            Okres=0,
            WIBORProcent=4.82,
            MarzaFinansowaProcent=2.0,
        )
        calc = FinanseCalculator(inp)
        result = calc.calculate()
        assert result.SumaOdsetekZczynszem == 0.0
        assert result.SumaOdsetekBEZczynszu == 0.0

    def test_wp_zero(self) -> None:
        """WP = 0 → ValueError."""
        inp = FinanseInput(
            WartoscPoczatkowaNetto=0.0,
            WrPrzewidywanaCenaSprzedazy=46_000.0,
            CzynszInicjalny=0.0,
            CzynszProcent=0.0,
            RodzajCzynszu="Kwotowo",
            StawkaVAT=1.23,
            Okres=48,
            WIBORProcent=4.82,
            MarzaFinansowaProcent=2.0,
        )
        with pytest.raises(ValueError):
            FinanseCalculator(inp).calculate()

    def test_wr_wieksze_niz_kredyt(self) -> None:
        """WR > kredyt → wykup = kredyt (min constraint)."""
        inp = FinanseInput(
            WartoscPoczatkowaNetto=50_000.0,
            WrPrzewidywanaCenaSprzedazy=60_000.0,
            CzynszInicjalny=0.0,
            CzynszProcent=0.0,
            RodzajCzynszu="Kwotowo",
            StawkaVAT=1.23,
            Okres=48,
            WIBORProcent=4.82,
            MarzaFinansowaProcent=2.0,
        )
        calc = FinanseCalculator(inp)
        result = calc.calculate()
        assert abs(result.WykupKwota - 50_000.0) < 0.01
