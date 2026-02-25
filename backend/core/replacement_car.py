from typing import Dict, Any, Optional


class ReplacementCarCalculator:
    """Moduł odpowiedzialny za kalkulację kosztu samochodu zastępczego (LTR_V1)"""

    def __init__(self, stawka_zastepcza_data: Optional[Dict[str, Any]]):
        """
        stawka_zastepcza_data: słownik z danymi z ltr_admin_stawka_zastepczy
        """
        self.stawka_data = stawka_zastepcza_data or {}

        # SredniaIloscDobWRoku - jak często auto trafia do zastępczego (np. 5 dni/rok)
        self.srednia_dni_w_roku = float(
            self.stawka_data.get("SredniaIloscDobWRoku", 0.0)
        )
        # DobaNetto - stawka wynajmu za jeden dzień
        self.doba_netto = float(self.stawka_data.get("DobaNetto", 0.0))

    def calculate_cost(self, months: int, enabled: bool) -> Dict[str, Any]:
        """
        Zwraca pełen i miesięczny koszt auta zastępczego (wchodzi na płasko w Technical)
        - months: Czas trwania leasingu/wynajmu
        - enabled: Czy checkbox włączony w UI
        """
        if not enabled or self.srednia_dni_w_roku == 0.0 or self.doba_netto == 0.0:
            return {"total_replacement_car": 0.0, "monthly_replacement_car": 0.0}

        years = months / 12.0

        # Prosta zryczałtowana matematyka z V1
        total_days = self.srednia_dni_w_roku * years
        total_cost = total_days * self.doba_netto

        return {
            "total_replacement_car": round(total_cost, 2),
            "monthly_replacement_car": round(total_cost / months, 2)
            if months > 0
            else 0.0,
        }
