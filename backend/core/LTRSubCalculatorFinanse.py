"""
LTRSubCalculatorFinanse — port V1 LTRSubCalculatorFinanse.cs + PMT.cs

Oblicza koszty finansowe (PMT) z pełnym harmonogramem rat i dwoma wariantami:
  1. Z czynszem inicjalnym (kredyt = WP − czynsz/VAT)
  2. Bez czynszu inicjalnego (kredyt = WP, ten sam wykup)

Formuła PMT identyczna z V1 PMT.cs L28:
    K = −kapitalDoSplaty
    im = oprocentowanie / 12
    imN = (1 + im) ^ n
    pmt = ((K × imN + W) × im) / (1 − imN)
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Rata:
    """Pojedyncza rata w harmonogramie spłat (V1: Rata class)."""

    NumerRaty: int = 0
    KapitalDoSplaty: float = 0.0
    RataLeasingowa: float = 0.0
    RataKapitalowa: float = 0.0
    KapitalPoSplacie: float = 0.0
    RataOdsetkowa: float = 0.0


@dataclass
class FinanseInput:
    """Dane wejściowe — nazewnictwo V1."""

    WartoscPoczatkowaNetto: float  # Pełny CAPEX netto
    WrPrzewidywanaCenaSprzedazy: float  # WR netto (z samar_rv)
    Okres: int  # Liczba miesięcy (rat)
    WIBORProcent: float  # WIBOR % (z control_center)
    MarzaFinansowaProcent: float  # Marża % (z control_center)

    # Czynsz inicjalny — kwotowy LUB procentowy
    RodzajCzynszu: str = "Kwotowo"  # "Kwotowo" | "Procentowo"
    CzynszInicjalny: float = 0.0  # Kwota BRUTTO (tryb kwotowy)
    CzynszProcent: float = 0.0  # % od WP netto (tryb procentowy)
    StawkaVAT: float = 1.23  # Do konwersji brutto → netto


@dataclass
class FinanseResult:
    """Wynik — V1 Result + harmonogram rat."""

    # Wariant Z czynszem
    SumaOdsetekZczynszem: float = 0.0
    monthly_pmt_z_czynszem: float = 0.0
    RatyZczynszem: List[Rata] = field(default_factory=list)

    # Wariant BEZ czynszu
    SumaOdsetekBEZczynszu: float = 0.0
    monthly_pmt_bez_czynszu: float = 0.0
    RatyBezCzynszu: List[Rata] = field(default_factory=list)

    # Metadata
    CzynszInicjalnyProcent: float = 0.0
    CzynszInicjalnyNetto: float = 0.0
    MarzaFinansowaProcent: float = 0.0
    WykupKwota: float = 0.0
    Oprocentowanie: float = 0.0


def _pmt_v1(
    kapital: float,
    wykup: float,
    oprocentowanie: float,
    liczba_rat: int,
) -> float:
    """
    Formuła PMT identyczna z V1 PMT.cs L15-37.

    K = -kapitalDoSplaty
    im = oprocentowanie / 12
    imN = (1 + im) ^ n
    pmt = ((K * imN + W) * im) / (1 - imN)
    """
    if liczba_rat <= 0:
        return 0.0

    im = oprocentowanie / 12.0
    if im == 0.0:
        return (kapital - wykup) / liczba_rat

    # V1: pozostaloRat = liczbaRat + 1 - nrRaty; dla nrRaty=1 → n
    im_n = (1.0 + im) ** liczba_rat

    if im_n == 1.0:
        raise ValueError("Nie można policzyć PMT: imN == 1")

    k_neg = -kapital  # V1 L18: kapitalDoSplaty * (-1)
    pmt = ((k_neg * im_n + wykup) * im) / (1.0 - im_n)
    return pmt


def _get_raty(
    wartosc_kredytu: float,
    wykup_kwota: float,
    ilosc_rat: int,
    oprocentowanie: float,
) -> tuple[List[Rata], float, float]:
    """
    Port V1 getRaty() L138-188.

    Iteracyjny harmonogram spłat z rozbiciem na ratę odsetkową
    i kapitałową. Zwraca (lista_rat, suma_odsetek, rata_kwota).
    """
    if ilosc_rat <= 0:
        return [], 0.0, 0.0

    rata_kwota = _pmt_v1(wartosc_kredytu, wykup_kwota, oprocentowanie, ilosc_rat)

    raty: List[Rata] = []
    im = oprocentowanie / 12.0

    for r in range(1, ilosc_rat + 1):
        rata = Rata(NumerRaty=r)

        if r == 1:
            rata.KapitalDoSplaty = wartosc_kredytu
        else:
            rata.KapitalDoSplaty = raty[-1].KapitalPoSplacie

        rata.RataLeasingowa = rata_kwota
        rata.RataOdsetkowa = rata.KapitalDoSplaty * im
        rata.RataKapitalowa = rata.RataLeasingowa - rata.RataOdsetkowa
        rata.KapitalPoSplacie = rata.KapitalDoSplaty - rata.RataKapitalowa

        raty.append(rata)

    suma_odsetek = sum(r.RataOdsetkowa for r in raty)
    return raty, suma_odsetek, rata_kwota


class FinanseCalculator:
    """
    LTRSubCalculatorFinanse — kalkulacja kosztów finansowych (PMT).

    Port V1 LTRSubCalculatorFinanse.cs (194 linii) + PMT.cs (51 linii).
    """

    def __init__(self, data: FinanseInput) -> None:
        self.data = data

    def _resolve_czynsz_netto(self) -> float:
        """Rozwiązuje czynsz netto z kwoty brutto lub %."""
        if self.data.RodzajCzynszu == "Procentowo":
            return self.data.WartoscPoczatkowaNetto * (self.data.CzynszProcent / 100.0)
        # Kwotowo: brutto / VAT = netto (V1 L61)
        if self.data.StawkaVAT <= 0:
            return self.data.CzynszInicjalny
        return self.data.CzynszInicjalny / self.data.StawkaVAT

    def calculate(self) -> FinanseResult:
        wp = self.data.WartoscPoczatkowaNetto
        wr = self.data.WrPrzewidywanaCenaSprzedazy
        okres = self.data.Okres

        if okres <= 0:
            return FinanseResult()

        if wp <= 0:
            raise ValueError("Parametr WartoscPoczatkowaNetto nie może być <= 0")

        # Czynsz netto
        czynsz_netto = self._resolve_czynsz_netto()
        czynsz_procent = (czynsz_netto / wp * 100.0) if wp > 0 else 0.0

        # Oprocentowanie = WIBOR + Marża (V1 L67)
        oprocentowanie = (
            self.data.WIBORProcent + self.data.MarzaFinansowaProcent
        ) / 100.0

        # --- Wariant Z CZYNSZEM (V1 L61, L71) ---
        wartosc_kredytu = wp - czynsz_netto
        wykup_kwota = min(wartosc_kredytu, wr)  # V1 L63

        raty_z, suma_z, pmt_z = _get_raty(
            wartosc_kredytu, wykup_kwota, okres, oprocentowanie
        )

        # --- Wariant BEZ CZYNSZU (V1 L73) ---
        # V1: ten sam wykup_kwota, ale kredyt = pełne WP
        raty_bez, suma_bez, pmt_bez = _get_raty(wp, wykup_kwota, okres, oprocentowanie)

        return FinanseResult(
            SumaOdsetekZczynszem=suma_z,
            monthly_pmt_z_czynszem=pmt_z,
            RatyZczynszem=raty_z,
            SumaOdsetekBEZczynszu=suma_bez,
            monthly_pmt_bez_czynszu=pmt_bez,
            RatyBezCzynszu=raty_bez,
            CzynszInicjalnyProcent=czynsz_procent,
            CzynszInicjalnyNetto=czynsz_netto,
            MarzaFinansowaProcent=self.data.MarzaFinansowaProcent,
            WykupKwota=wykup_kwota,
            Oprocentowanie=oprocentowanie,
        )
