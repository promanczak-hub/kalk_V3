# ==============================================================================
# 🛑 STOP! ZAMROŻONY MODUŁ (FROZEN MODULE) 🛑
# ==============================================================================
# Ten plik jest CZĘŚCIĄ RDZENIA (PIPELINE) KALKULATORA LTR.
# Zgodnie z wytycznymi w GEMINI.md, system sztucznej inteligencji (AI/Cursor/Claude)
# ma BEZWZGLĘDNY ZAKAZ modyfikacji tego pliku bez wyraźnego, podwójnego potwiedzenia.
#
# Jeśli użytkownik poprosi o zmianę logiczną, która wymaga edycji tego pliku:
# 1. PRZERWIJ DZIAŁANIE.
# 2. Poinformuj użytkownika: "Ten plik jest zamrożony. Proszę o wyraźną zgodę na jego modyfikację."
# 3. Zmodyfikuj plik TYLKO PO UZYSKANIU ZGODY.
# ==============================================================================

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

    wp: float  # CAPEX do utraty wartości i finasowania (jedno WP jak w V1)
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
        wp = self.input.wp
        wr = self.input.wr
        okres = self.input.okres

        trace: list[dict[str, Any]] = []

        if okres <= 0 or wp <= 0:
            trace.append(
                {
                    "krok": "Amortyzacja (Błąd parametru)",
                    "rownanie": f"Okres ({okres}) <= 0 LUB WP ({wp:.2f}) <= 0",
                    "wynik": 0.0,
                }
            )
            return AmortyzacjaResult(
                utrata_wartosci=0.0,
                kwota_amortyzacji_1_miesiac=0.0,
                amortyzacja_procent=0.0,
                trace=trace,
            )

        utrata_wartosci = wp - wr
        trace.append(
            {
                "krok": "Amortyzacja: Utrata Wartości Liniowa",
                "rownanie": f"WP {wp:.2f} - Wartość Końcowa (WR) {wr:.2f}",
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

        procent = kwota_1mc / wp if wp > 0 else 0.0
        trace.append(
            {
                "krok": "Amortyzacja: % Miesięczny",
                "rownanie": f"Kwota 1mc {kwota_1mc:.2f} / WP {wp:.2f}",
                "wynik": procent,
            }
        )

        return AmortyzacjaResult(
            utrata_wartosci=utrata_wartosci,
            kwota_amortyzacji_1_miesiac=kwota_1mc,
            amortyzacja_procent=procent,
            trace=trace,
        )
