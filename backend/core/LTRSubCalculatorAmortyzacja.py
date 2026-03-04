"""
LTRSubCalculatorAmortyzacja – port V1 LTRSubCalculatorAmortyzacja.cs

Oblicza miesięczny procent amortyzacji liniowej na podstawie
Wartości Początkowej (WP), Wartości Rezydualnej (WR) i okresu.
"""

from dataclasses import dataclass


@dataclass
class AmortyzacjaInput:
    """Dane wejściowe sub-kalkulatora amortyzacji."""

    wp: float  # Wartość Początkowa netto (Cena zakupu)
    wr: float  # Wartość Rezydualna netto
    okres: int  # Liczba miesięcy kontraktu


@dataclass
class AmortyzacjaResult:
    """Wynik sub-kalkulatora amortyzacji."""

    utrata_wartosci: float  # WP - WR
    kwota_amortyzacji_1_miesiac: float  # utrata / okres
    amortyzacja_procent: float  # kwota_1mc / WP (miesięczny %)


class AmortyzacjaCalculator:
    """
    LTRSubCalculatorAmortyzacja – kalkulator % amortyzacji.

    Logika V1: amortyzacja liniowa.
        utrataWartosci = WP - WR
        kwotaAmortyzacji1Miesiac = utrataWartosci / Okres
        procentAmortyzacji = kwotaAmortyzacji1Miesiac / WP
    """

    def __init__(self, input_data: AmortyzacjaInput) -> None:
        self.input = input_data

    def calculate(self) -> AmortyzacjaResult:
        wp = self.input.wp
        wr = self.input.wr
        okres = self.input.okres

        if okres <= 0 or wp <= 0:
            return AmortyzacjaResult(
                utrata_wartosci=0.0,
                kwota_amortyzacji_1_miesiac=0.0,
                amortyzacja_procent=0.0,
            )

        utrata_wartosci = wp - wr
        kwota_1mc = utrata_wartosci / okres
        procent = kwota_1mc / wp

        return AmortyzacjaResult(
            utrata_wartosci=utrata_wartosci,
            kwota_amortyzacji_1_miesiac=kwota_1mc,
            amortyzacja_procent=procent,
        )
