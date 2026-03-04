from typing import Dict, Any
from core.database import supabase


class ReplacementCarCalculator:
    """Moduł odpowiedzialny za kalkulację kosztu samochodu zastępczego (LTR_V1)"""

    def __init__(self, samar_class_id: int):
        """
        Inicjalizacja na podstawie ID klasy SAMAR.
        Pobiera stawki bezpośrednio z bazy danych z tabeli replacement_car_rates.
        """
        self.samar_class_id = samar_class_id
        self.average_days_per_year = 0.0
        self.daily_rate_net = 0.0

        self._fetch_rates()

    def _fetch_rates(self):
        """Pobiera stawki z tabeli replacement_car_rates na podstawie samar_class_id."""
        try:
            res = (
                supabase.table("replacement_car_rates")
                .select("average_days_per_year, daily_rate_net")
                .eq("samar_class_id", self.samar_class_id)
                .execute()
            )

            if res.data:
                self.average_days_per_year = float(res.data[0]["average_days_per_year"])
                self.daily_rate_net = float(res.data[0]["daily_rate_net"])
        except Exception as e:
            print(f"Błąd pobierania stawek ZRW dla klasy {self.samar_class_id}: {e}")

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
