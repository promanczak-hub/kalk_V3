from typing import Dict, Any


class ReplacementCarCalculator:
    """Moduł odpowiedzialny za kalkulację kosztu samochodu zastępczego (LTR_V1)"""

    def __init__(self, rate_data: Dict[str, Any]):
        """
        Inicjalizacja na podstawie danych stawki pobranej z tabeli replacement_car_rates.
        rate_data pochodzi z tabeli replacement_car_rates (per klasa SAMAR).
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
        trace: list[dict[str, Any]] = []

        if not enabled or months == 0:
            trace.append(
                {
                    "krok": "Auto Zastępcze (Wyłączone)",
                    "rownanie": "enabled = False",
                    "wynik": 0.0,
                }
            )
            return {
                "total_replacement_car": 0.0,
                "monthly_replacement_car": 0.0,
                "trace": trace,
            }

        if self.average_days_per_year == 0.0 or self.daily_rate_net == 0.0:
            raise ValueError(
                "Koszty samochodu zastępczego uaktywnione, ale brak stawek (Dni/Raty) w 'replacement_car_rates'. Kalkulacja przerwana."
            )

        years = months / 12.0
        total_days = self.average_days_per_year * years

        trace.append(
            {
                "krok": "Auto Zastępcze: Ilość Dni",
                "rownanie": f"Średnia roczna z bazy: {self.average_days_per_year:.2f} dni * {years:.2f} lat",
                "wynik": total_days,
            }
        )

        total_cost = total_days * self.daily_rate_net

        trace.append(
            {
                "krok": "Auto Zastępcze: Łączny Koszt",
                "rownanie": f"Łącznie {total_days:.2f} dni * Stawka Netto {self.daily_rate_net:.2f} PLN",
                "wynik": total_cost,
            }
        )

        return {
            "total_replacement_car": round(total_cost, 2),
            "monthly_replacement_car": round(total_cost / months, 2),
            "trace": trace,
        }
