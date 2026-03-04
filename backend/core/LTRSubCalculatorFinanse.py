from dataclasses import dataclass


@dataclass
class FinanceInput:
    total_capex: float
    upfront_pct: float
    rv_net: float
    months: int
    wibor_pct: float
    margin_pct: float


@dataclass
class FinanceResult:
    monthly_pmt_net: float
    total_pmt_cost: float
    total_interest: float
    total_capital_repayment: float
    initial_deposit_net: float


class FinanceCalculator:
    """
    LTRSubCalculatorFinanse - Moduł odpowiedzialny za wyliczanie raty PMT,
    oprocentowania (Wibor + Marża) i rozbicia marży odsetkowej zgodnie z architekturą V1.
    """

    def __init__(self, input_data: FinanceInput):
        self.input = input_data

    def calculate(self) -> FinanceResult:
        if self.input.months <= 0:
            return FinanceResult(0.0, 0.0, 0.0, 0.0, 0.0)

        # Oprocentowanie = Wibor + Marża Finansowa
        rate = (self.input.wibor_pct + self.input.margin_pct) / 100.0 / 12.0
        n_periods = self.input.months

        # Kapitał (PV)
        # Obniżany o ułamek czynszu wpłaty początkowej
        upfront_value = self.input.total_capex * (self.input.upfront_pct / 100.0)
        pv = self.input.total_capex - upfront_value

        # Wartość Wykupu (FV) - Otrzymana z kalkulatora wartości rezydualnej wprost w netto (rv_net)
        fv = self.input.rv_net

        # Zgodnie z NotebookLM V1 (reguła V1): Wykup na harmonogramie spłat nigdy nie był wyższy niż wartość kredytu
        fv = min(fv, pv)

        if rate == 0:
            pmt = (pv - fv) / n_periods
            total_interest = 0.0
            return FinanceResult(
                monthly_pmt_net=pmt,
                total_pmt_cost=pmt * n_periods,
                total_interest=total_interest,
                total_capital_repayment=pv - fv,
                initial_deposit_net=upfront_value,
            )
        else:
            # Wzór annuitetowy V1 na PMT
            pmt = (rate * (pv - fv / ((1 + rate) ** n_periods))) / (
                1 - (1 + rate) ** -n_periods
            )
            total_interest = (pmt * n_periods) - (pv - fv)

        return FinanceResult(
            monthly_pmt_net=pmt,
            total_pmt_cost=pmt * n_periods,
            total_interest=total_interest,
            total_capital_repayment=pv - fv,
            initial_deposit_net=upfront_value,
        )
