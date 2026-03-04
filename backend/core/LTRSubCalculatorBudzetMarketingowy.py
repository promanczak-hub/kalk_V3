"""
LTRSubCalculatorBudzetMarketingowy – port V1 LTRSubCalculatorBudzetMarketingowy.cs

Kalkulacja korekty WR maks brutto z tytułu budżetu marketingowego.
Wynik = WR * StawkaVAT * BudzetMarketingowyLtr
"""

from dataclasses import dataclass


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


class BudzetMarketingowyCalculator:
    """
    LTRSubCalculatorBudzetMarketingowy – korekta WR z budżetu mktg.

    Logika V1:
        korektaWRMaksBrutto = WR * StawkaVAT * BudzetMarketingowyLtr
    """

    def __init__(self, input_data: BudzetMarketingowyInput) -> None:
        self.input = input_data

    def calculate(self) -> BudzetMarketingowyResult:
        korekta = (
            self.input.wr_przewidywana_cena_sprzedazy
            * self.input.stawka_vat
            * self.input.budzet_marketingowy_ltr
        )

        return BudzetMarketingowyResult(korekta_wr_maks=korekta)
