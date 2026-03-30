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
LTRSubCalculatorBudzetMarketingowy – port V1 LTRSubCalculatorBudzetMarketingowy.cs

Kalkulacja korekty WR maks brutto z tytułu budżetu marketingowego.
Wynik = WR * StawkaVAT * BudzetMarketingowyLtr
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BudzetMarketingowyInput:
    """Dane wejściowe sub-kalkulatora budżetu marketingowego."""

    wr_przewidywana_cena_sprzedazy: float  # WR netto
    stawka_vat: float  # np. 1.23 (mnożnik brutto)
    budzet_marketingowy_ltr: float  # parametr % z control_center


@dataclass
class BudzetMarketingowyResult:
    """Wynik sub-kalkulatora budżetu marketingowego."""

    korekta_wr_maks: float  # Maksymalna korekta WR brutto
    trace: list[dict[str, Any]] = field(default_factory=list)


class BudzetMarketingowyCalculator:
    """
    LTRSubCalculatorBudzetMarketingowy – korekta WR z budżetu mktg.

    Logika V1:
        korektaWRMaksBrutto = WR * StawkaVAT * BudzetMarketingowyLtr
    """

    def __init__(self, input_data: BudzetMarketingowyInput) -> None:
        self.input = input_data

    def calculate(self) -> BudzetMarketingowyResult:
        trace: list[dict[str, Any]] = []
        korekta = (
            self.input.wr_przewidywana_cena_sprzedazy
            * self.input.stawka_vat
            * self.input.budzet_marketingowy_ltr
        )

        trace.append(
            {
                "krok": "Budżet Marketingowy",
                "rownanie": f"WR Netto ({self.input.wr_przewidywana_cena_sprzedazy:.2f}) * VAT ({self.input.stawka_vat:.2f}) * Budżet% ({self.input.budzet_marketingowy_ltr * 100:.2f}%)",
                "wynik": korekta,
            }
        )

        return BudzetMarketingowyResult(korekta_wr_maks=korekta, trace=trace)
