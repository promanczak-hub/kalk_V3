from typing import Dict, Any


class ReplacementCarCalculator:
    """Moduł odpowiedzialny za kalkulację kosztu samochodu zastępczego (LTR_V1)"""

    def __init__(self, rate_data: Dict[str, Any]):
        """
        Inicjalizacja na podstawie danych stawki pobranej z tabeli replacement_car_rates.
        rate_data może pochodzić z replacement_car_rates lub ltr_admin_stawka_zastepczy.
        """
        self.average_days_per_year = float(
            rate_data.get("average_days_per_year", 0.0)
            or rate_data.get("SredniaIloscDobWRoku", 0.0)
        )
        self.daily_rate_net = float(
            rate_data.get("daily_rate_net", 0.0) or rate_data.get("DobaNetto", 0.0)
        )

    def calculate_cost(self, months: int, enabled: bool) -> Dict[str, Any]:
        """
        Zwraca pełen i miesięczny koszt auta zastępczego (wchodzi na płasko w Technical)
        - months: Czas trwania leasingu/wynajmu
        - enabled: Czy checkbox włączony w UI
        """
        if (
            not enabled
            or self.average_days_per_year == 0.0
            or self.daily_rate_net == 0.0
            or months == 0
        ):
            return {"total_replacement_car": 0.0, "monthly_replacement_car": 0.0}

        years = months / 12.0
        total_days = self.average_days_per_year * years
        total_cost = total_days * self.daily_rate_net

        return {
            "total_replacement_car": round(total_cost, 2),
            "monthly_replacement_car": round(total_cost / months, 2),
        }
