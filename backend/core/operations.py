from typing import Any, Dict


class OperationalCostsCalculator:
    """Moduł agregujący koszty serwisowe i ubezpieczeniowe."""

    def __init__(self, samar_klasa_data: Dict[str, Any]):
        self.samar_klasa_data = samar_klasa_data
        self.insurance_rate = 0.03  # 3% bazowe ubezpieczenie wartości (Można to zaciągnąć ze stawek ubezp w przyszłości)

        # Pobierz config serwisu dla klasy (fallback do uśrednionych jeśli config pusty)
        self.stawka_serwis_km = float(
            self.samar_klasa_data.get("stawka_serwis_km", 0.12)
        )
        self.koszt_przegladu_podstawowego = float(
            self.samar_klasa_data.get("koszt_przegladu_podstawowego", 1500.0)
        )

    def calculate_cost(
        self, months: int, total_km: int, capex: float
    ) -> Dict[str, Any]:

        # Nowy model Serwisowy (Smart Service) w oparciu o wytyczne biznesowe:
        # 1. Baza ryczałtowa za robótki km
        total_service_from_km = total_km * self.stawka_serwis_km

        # 2. Minimalna poduszka bezpieczeństwa wynikająca z obowiązkowych letargu (1 na rok wynajmu)
        years = months / 12.0
        min_total_service = years * self.koszt_przegladu_podstawowego

        # Bierzemy dla pewności wyższą wartość
        total_service = max(total_service_from_km, min_total_service)

        return {
            "total_service": round(total_service, 2),
            "monthly_service": round(total_service / months, 2),
            "debug": {
                "service_from_km": round(total_service_from_km, 2),
                "service_min_flat": round(min_total_service, 2),
            },
        }
