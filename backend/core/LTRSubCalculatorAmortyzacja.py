"""
LTRSubCalculatorAmortyzacja – port V1 LTRSubCalculatorAmortyzacja.cs

Oblicza miesięczny procent amortyzacji liniowej na podstawie
Wartości Początkowej (WP), Wartości Rezydualnej (WR) i okresu.
"""

from dataclasses import dataclass


from typing import Any


@dataclass
class AmortyzacjaInput:
    """Dane wejściowe sub-kalkulatora amortyzacji."""

    wp_finansowanie: float  # CAPEX pełny do finansowania (np. z oponami)
    wp_amortyzacja: float  # CAPEX pomniejszony używany do samej utraty wartości (pojazd + opcje fabr)
    wr: float  # Wartość Rezydualna netto
    okres: int  # Liczba miesięcy kontraktu


@dataclass
class AmortyzacjaResult:
    """Wynik sub-kalkulatora amortyzacji."""

    utrata_wartosci: float  # WP - WR
    kwota_amortyzacji_1_miesiac: float  # utrata / okres
    amortyzacja_procent: float  # kwota_1mc / WP (miesięczny %)
    trace: list[dict[str, Any]]


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
        wp_finansowanie = self.input.wp_finansowanie
        wp_amortyzacja = self.input.wp_amortyzacja
        wr = self.input.wr
        okres = self.input.okres

        trace: list[dict[str, Any]] = []

        if okres <= 0 or wp_amortyzacja <= 0:
            trace.append(
                {
                    "krok": "Amortyzacja (Błąd parametru)",
                    "rownanie": f"Okres ({okres}) <= 0 LUB WP Amortyzacji ({wp_amortyzacja:.2f}) <= 0",
                    "wynik": 0.0,
                }
            )
            return AmortyzacjaResult(
                utrata_wartosci=0.0,
                kwota_amortyzacji_1_miesiac=0.0,
                amortyzacja_procent=0.0,
                trace=trace,
            )

        utrata_wartosci = wp_amortyzacja - wr
        trace.append(
            {
                "krok": "Amortyzacja: Utrata Wartości Liniowa",
                "rownanie": f"WP_Amortyzacji {wp_amortyzacja:.2f} - Wartość Końcowa (WR) {wr:.2f}",
                "wynik": utrata_wartosci,
            }
        )

        kwota_1mc = utrata_wartosci / okres
        trace.append(
            {
                "krok": "Amortyzacja: Kwota Miesięczna",
                "rownanie": f"Utrata {utrata_wartosci:.2f} / Okres {okres} msc",
                "wynik": kwota_1mc,
            }
        )

        procent = kwota_1mc / wp_finansowanie
        trace.append(
            {
                "krok": "Amortyzacja: % Miesięczny dla Ubezpieczenia (Stosunek Liniowy)",
                "rownanie": f"Kwota 1mc {kwota_1mc:.2f} / WP_Finansowania {wp_finansowanie:.2f}. Wymóg dla symulacji V1 (ubezpieczenie liczone od pełnego capexu).",
                "wynik": procent,
            }
        )

        return AmortyzacjaResult(
            utrata_wartosci=utrata_wartosci,
            kwota_amortyzacji_1_miesiac=kwota_1mc,
            amortyzacja_procent=procent,
            trace=trace,
        )
