"""
LTRSubCalculatorStawka – port V1 LTRSubCalculatorStawka.cs (311 linii)

Kalkulacja oferowanej stawki miesięcznej i pełnego rozkładu marży
na 6 składników kosztowych (finansowy, ubezpieczenie, samochód zastępczy,
serwis, opony, admin/koszty dodatkowe).

Obsługuje korekty ręczne podziału marży (MarzaKosztFinansowyProcent itp.).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KosztItem:
    """Pojedynczy składnik kosztowy z rozkładem marży (V1: Koszt class)."""

    name: str
    koszty_laczne: float = 0.0  # Suma kosztów łącznych netto
    koszt_mc: float = 0.0  # Koszt miesięczny
    rozklad_marzy: float = 0.0  # Automatyczny podział marży (waga)
    rozklad_marzy_korekta: float = 0.0  # Korekta ręczna (lub auto)
    marza_dla_kalk: float = 0.0  # Używana marża (= korekta lub auto)
    kwota_marzy: float = 0.0  # MarzaMC * RozkladMarzy
    kwota_marzy_korekta: float = 0.0  # MarzaMC * RozkladMarzyKorekta
    koszt_plus_marza: float = 0.0  # KosztMC + KwotaMarzy
    koszt_plus_marza_korekta: float = 0.0  # KosztMC + KwotaMarzyKorekta


@dataclass
class StawkaInput:
    """Dane wejściowe sub-kalkulatora stawki."""

    koszt_mc: float  # KosztDzienny.Result.koszt_mc
    koszt_mc_bez_czynszu: float  # KosztDzienny.Result.koszt_mc_bez_czynszu
    utrata_wartosci_netto: float  # UtrataWartości z czynszem
    koszty_finansowe_netto: float  # Suma odsetek z czynszem
    ubezpieczenie_netto: float  # Łączne ubezpieczenie
    samochod_zastepczy_netto: float
    koszty_dodatkowe_netto: float
    opony_netto: float
    serwis_netto: float
    okres: int  # Liczba miesięcy
    marza: float  # Marża jako ułamek (np. 0.08 = 8%)
    czynsz_inicjalny: float  # Wartość czynszu inicjalnego netto
    # Opcjonalne korekty ręczne podziału marży
    marza_koszt_finansowy_pct: Optional[float] = None
    marza_ubezpieczenie_pct: Optional[float] = None
    marza_samochod_zastepczy_pct: Optional[float] = None
    marza_serwis_pct: Optional[float] = None
    marza_opony_pct: Optional[float] = None
    marza_koszty_dodatkowe_pct: Optional[float] = None


@dataclass
class StawkaResult:
    """Wynik sub-kalkulatora stawki."""

    czynsz_finansowy: float = 0.0
    czynsz_techniczny: float = 0.0
    oferowana_stawka: float = 0.0  # CF + CT
    podstawa_marzy: float = 0.0
    przychod: float = 0.0
    marza_mc: float = 0.0
    marza_na_kontrakcie: float = 0.0
    marza_na_kontrakcie_procent: float = 0.0
    koszty_laczne_mc: float = 0.0
    koszt_finansowy_lacznie: float = 0.0
    koszt_finansowy_miesiecznie: float = 0.0
    # Rozklad po korektach
    koszt_finansowy: KosztItem = field(default_factory=lambda: KosztItem(""))
    koszt_ubezpieczenie: KosztItem = field(default_factory=lambda: KosztItem(""))
    koszt_samochod_zastepczy: KosztItem = field(default_factory=lambda: KosztItem(""))
    koszt_serwis: KosztItem = field(default_factory=lambda: KosztItem(""))
    koszt_opony: KosztItem = field(default_factory=lambda: KosztItem(""))
    koszt_admin: KosztItem = field(default_factory=lambda: KosztItem(""))


class StawkaCalculator:
    """
    LTRSubCalculatorStawka – kalkulacja oferowanej stawki V1.

    Rozkład marży na 6 składników:
        1. Koszt Finansowy (utrata wartości + odsetki)
        2. Ubezpieczenie
        3. Samochód Zastępczy
        4. Serwis
        5. Opony
        6. Koszty Dodatkowe (Admin / rejestracja)

    Logika V1 (LTRSubCalculatorStawka.cs):
        - podstawaMarzy = jeśli CzynszInicjalny==0 → KosztMC,
                          w przeciwnym razie → KosztMC_BEZ_czynszu
        - marzaMC = podstawaMarzy * (1 / (1 - marza)) - podstawaMarzy
        - Rozkład proporcjonalny wg udziału kosztMC / kosztyŁączneMC
        - Korekty ręczne zastępują auto-podział
    """

    def __init__(self, input_data: StawkaInput) -> None:
        self.input = input_data

    def _get_koszty_laczne_mc(self) -> float:
        """Sumuje wszystkie koszty w ujęciu miesięcznym."""
        d = self.input
        if d.okres <= 0:
            return 0.0

        total = (
            d.koszty_finansowe_netto
            + d.utrata_wartosci_netto
            + d.ubezpieczenie_netto
            + d.samochod_zastepczy_netto
            + d.serwis_netto
            + d.opony_netto
            + d.koszty_dodatkowe_netto
        )
        return total / d.okres

    def _build_koszt(
        self,
        name: str,
        koszty_laczne: float,
        koszty_laczne_mc: float,
        marza_mc: float,
        korekta_override: Optional[float],
    ) -> KosztItem:
        """Buduje KosztItem z automatycznym lub ręcznym podziałem marży."""
        okres = self.input.okres
        if okres <= 0 or koszty_laczne_mc == 0.0:
            return KosztItem(name=name)

        koszt_mc = koszty_laczne / okres
        rozklad = koszt_mc / koszty_laczne_mc if koszty_laczne_mc != 0 else 0.0
        rozklad_korekta = korekta_override if korekta_override is not None else rozklad
        marza_dla_kalk = rozklad_korekta if koszt_mc != 0 else 0.0

        return KosztItem(
            name=name,
            koszty_laczne=koszty_laczne,
            koszt_mc=koszt_mc,
            rozklad_marzy=rozklad,
            rozklad_marzy_korekta=rozklad_korekta,
            marza_dla_kalk=marza_dla_kalk,
            kwota_marzy=marza_mc * rozklad,
            kwota_marzy_korekta=marza_mc * rozklad_korekta,
            koszt_plus_marza=koszt_mc + marza_mc * rozklad,
            koszt_plus_marza_korekta=koszt_mc + marza_mc * rozklad_korekta,
        )

    def calculate(self) -> StawkaResult:
        d = self.input

        if d.okres <= 0:
            return StawkaResult()

        marza = d.marza
        if (1.0 - marza) == 0.0:
            raise ValueError("Nie można przeliczyć: 1 - marza = 0")

        koszty_laczne_mc = self._get_koszty_laczne_mc()

        # Podstawa marży: zależy od czynszu inicjalnego
        if d.czynsz_inicjalny == 0.0:
            podstawa_marzy = d.koszt_mc
        else:
            podstawa_marzy = d.koszt_mc_bez_czynszu

        # Marża MC (V1: marzaMC = podstawaMarzy * (1 / (1 - marza)) - podstawaMarzy)
        marza_mc = podstawa_marzy * (1.0 / (1.0 - marza)) - podstawa_marzy
        marza_na_kontrakcie = marza_mc * d.okres

        # Budowa poszczególnych składników
        kf_laczne = d.koszty_finansowe_netto + d.utrata_wartosci_netto

        k_fin = self._build_koszt(
            "Koszt finansowy",
            kf_laczne,
            koszty_laczne_mc,
            marza_mc,
            d.marza_koszt_finansowy_pct,
        )
        k_ubezp = self._build_koszt(
            "Ubezpieczenie",
            d.ubezpieczenie_netto,
            koszty_laczne_mc,
            marza_mc,
            d.marza_ubezpieczenie_pct,
        )
        k_zastepczy = self._build_koszt(
            "Samochód zastępczy",
            d.samochod_zastepczy_netto,
            koszty_laczne_mc,
            marza_mc,
            d.marza_samochod_zastepczy_pct,
        )
        k_serwis = self._build_koszt(
            "Serwis",
            d.serwis_netto,
            koszty_laczne_mc,
            marza_mc,
            d.marza_serwis_pct,
        )
        k_opony = self._build_koszt(
            "Opony",
            d.opony_netto,
            koszty_laczne_mc,
            marza_mc,
            d.marza_opony_pct,
        )
        k_admin = self._build_koszt(
            "Serwis admin rej",
            d.koszty_dodatkowe_netto,
            koszty_laczne_mc,
            marza_mc,
            d.marza_koszty_dodatkowe_pct,
        )

        czynsz_fin = k_fin.koszt_plus_marza_korekta
        czynsz_tech = (
            k_ubezp.koszt_plus_marza_korekta
            + k_zastepczy.koszt_plus_marza_korekta
            + k_serwis.koszt_plus_marza_korekta
            + k_opony.koszt_plus_marza_korekta
            + k_admin.koszt_plus_marza_korekta
        )

        oferowana_stawka = czynsz_fin + czynsz_tech
        przychod = oferowana_stawka * d.okres

        marza_pct = marza_na_kontrakcie / przychod if przychod != 0 else 0.0

        return StawkaResult(
            czynsz_finansowy=czynsz_fin,
            czynsz_techniczny=czynsz_tech,
            oferowana_stawka=oferowana_stawka,
            podstawa_marzy=podstawa_marzy,
            przychod=przychod,
            marza_mc=marza_mc,
            marza_na_kontrakcie=marza_na_kontrakcie,
            marza_na_kontrakcie_procent=marza_pct,
            koszty_laczne_mc=koszty_laczne_mc,
            koszt_finansowy_lacznie=kf_laczne,
            koszt_finansowy_miesiecznie=kf_laczne / d.okres,
            koszt_finansowy=k_fin,
            koszt_ubezpieczenie=k_ubezp,
            koszt_samochod_zastepczy=k_zastepczy,
            koszt_serwis=k_serwis,
            koszt_opony=k_opony,
            koszt_admin=k_admin,
        )
