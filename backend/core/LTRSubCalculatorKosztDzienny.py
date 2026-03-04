"""
LTRSubCalculatorKosztDzienny – port V1 LTRSubCalculatorKosztDzienny.cs

Kalkulacja kosztu dziennego (i miesięcznego) kontraktu LTR.
Agreguje koszty: utrata wartości, finansowe, techniczne.
Oblicza też symulację BEZ czynszu inicjalnego.
"""

from dataclasses import dataclass

COEFF_KOSZT_DZIENNY: float = 30.4


@dataclass
class KosztDziennyInput:
    """Dane wejściowe sub-kalkulatora kosztu dziennego."""

    utrata_wartosci_z_czynszem: float  # UtrataWartościZCzynszemInicjalnym
    utrata_wartosci_bez_czynszu: float  # UtrataWartościBEZczynszu
    koszt_finansowy: float  # Suma odsetek Z czynszem
    samochod_zastepczy_netto: float
    koszty_dodatkowe_netto: float
    ubezpieczenie_netto: float
    opony_netto: float
    serwis_netto: float
    suma_odsetek_bez_czynszu: float  # Suma odsetek BEZ czynszu inic.
    okres: int  # Liczba miesięcy


@dataclass
class KosztDziennyResult:
    """Wynik sub-kalkulatora kosztu dziennego."""

    koszt_dzienny: float  # Netto / dzień
    koszty_ogolem: float  # Suma wszystkich kosztów
    koszt_mc: float  # Koszt miesięczny (z czynszem)
    koszt_mc_bez_czynszu: float  # Koszt MC symulowany (BEZ cz. inic.)


class KosztDziennyCalculator:
    """
    LTRSubCalculatorKosztDzienny – kalkulacja kosztu dziennego.

    Logika V1:
        łącznyKosztFinansowy = KosztFinansowy + UtrataWartościZczynszem
        łącznyKosztTechniczny = SamochodZastępczy + KosztyDodatkowe
                                + Ubezpieczenie + Opony + Serwis
        kosztyOgólem = łącznyFinansowy + łącznyTechniczny
        kosztyMiesiac = kosztyOgólem / Okres
        kosztDzienny = kosztyMiesiac / 30.4

    Symulacja BEZ czynszu:
        SYM_łącznyFinansowy = UtrataWartościBEZczynszu + SumaOdsetekBezCzynszu
        SYM_kosztyOgólem = SYM_łącznyFinansowy + łącznyKosztTechniczny
        SYM_kosztyMiesiac = SYM_kosztyOgólem / Okres
    """

    def __init__(self, input_data: KosztDziennyInput) -> None:
        self.input = input_data

    def calculate(self) -> KosztDziennyResult:
        d = self.input

        if d.okres <= 0:
            return KosztDziennyResult(
                koszt_dzienny=0.0,
                koszty_ogolem=0.0,
                koszt_mc=0.0,
                koszt_mc_bez_czynszu=0.0,
            )

        laczny_koszt_finansowy = d.koszt_finansowy + d.utrata_wartosci_z_czynszem

        laczny_koszt_techniczny = (
            d.samochod_zastepczy_netto
            + d.koszty_dodatkowe_netto
            + d.ubezpieczenie_netto
            + d.opony_netto
            + d.serwis_netto
        )

        koszty_ogolem = laczny_koszt_finansowy + laczny_koszt_techniczny
        koszty_miesiac = koszty_ogolem / d.okres
        koszt_dzienny = koszty_miesiac / COEFF_KOSZT_DZIENNY

        # Symulacja BEZ czynszu inicjalnego
        sym_laczny_finansowy = (
            d.utrata_wartosci_bez_czynszu + d.suma_odsetek_bez_czynszu
        )
        sym_koszty_ogolem = sym_laczny_finansowy + laczny_koszt_techniczny
        sym_koszty_miesiac = sym_koszty_ogolem / d.okres

        return KosztDziennyResult(
            koszt_dzienny=koszt_dzienny,
            koszty_ogolem=koszty_ogolem,
            koszt_mc=koszty_miesiac,
            koszt_mc_bez_czynszu=sym_koszty_miesiac,
        )
