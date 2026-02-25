from typing import Dict, Any


class FinancialCostsCalculator:
    """Moduł odpowiedzialny za kalkulację raty leasingowej z uwzględnieniem PMT."""

    def __init__(
        self, wibor_pct: float, margin_pct: float, initial_deposit_pct: float = 0.0
    ):
        self.wibor_pct = wibor_pct
        self.margin_pct = margin_pct
        self.initial_deposit_pct = initial_deposit_pct

    def calculate_cost(
        self, months: int, capex: float, rv_net: float
    ) -> Dict[str, Any]:
        """
        Zwraca pełen koszt finansowy na bazie parametrów:
        - months: L. miesiecy (np. 36)
        - capex: Pełna kwota wejściowa brutto (w tym Opcje/Opony - odpowiednik Ceny Zakupu)
        - rv_net: Przewidywana kwota wykupu (odpowiednik WR)
        """
        # 1. Czynsz Inicjalny (Wpłata Własna)
        initial_deposit_net = capex * (self.initial_deposit_pct / 100.0)

        # 2. Kwota faktycznie finansowana (Kapitał do spłaty)
        financed_capital = capex - initial_deposit_net

        # Zabezpieczenie przed ujemnym kredytem lub wyższym wykupem niż auto:
        financed_capital = max(0.0, financed_capital)
        wykup_kwota = min(financed_capital, rv_net)

        # 3. Oprocentowanie roczne (WIBOR + Marża)
        annual_rate = (self.wibor_pct + self.margin_pct) / 100.0

        # Oprocentowanie miesięczne
        monthly_rate = annual_rate / 12.0

        if monthly_rate == 0:
            # Leasing 0% przypadku brzegowego
            pmt = (financed_capital - wykup_kwota) / months
            total_interest = 0.0
            total_capital_repayment = financed_capital - wykup_kwota
            return {
                "monthly_pmt": round(pmt, 2),
                "total_interest": 0.0,
                "total_capital_repayment": round(total_capital_repayment, 2),
                "initial_deposit_net": round(initial_deposit_net, 2),
            }

        # 4. Obliczenie PMT dla malejącego kapitału (Formuła Bankowa LTR_V1 - Płatności z dołu)
        # Matematyka z PMT.cs: pmt = ((K * imN + W) * im) / (1 - imN) ... K ujemne w PMT.cs
        # Standardowe TVM PMT = (PV * r * (1+r)^n + FV * r) / ((1+r)^n - 1)
        # Przyrównując to do wzorów księgowych:

        pv = financed_capital
        fv = wykup_kwota
        r = monthly_rate
        n = months

        imN = (1 + r) ** n
        # PMT kalkuluje ile wynosi jednolita wpłata ratalna mając dzisiaj PV, a na koniec FV do spłaty
        pmt = (pv * r * imN - fv * r) / (imN - 1)

        # 5. Rozbicie PMT na odsetki i spłatę kapitału w całym okresie:
        # Suma rat = pmt * n
        # Z tego cała wpłacona gotówka to: suma rat + wykup + pierwsza wpłata
        # Odsetki całkowite = (Suma rat + wykup) - PV (bazowej kwoty wziętej)

        total_installments = pmt * n
        total_interest = (total_installments + fv) - pv
        total_capital_repayment = pv - fv

        return {
            "monthly_pmt": round(pmt, 2),
            "total_interest": round(total_interest, 2),
            "total_capital_repayment": round(total_capital_repayment, 2),
            "initial_deposit_net": round(initial_deposit_net, 2),
        }
