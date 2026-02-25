from typing import Dict, Any


class LTRSubCalculatorOpony:
    """Moduł odpowiedzialny za kalkulację kosztów opon."""

    def __init__(self, all_season_tires: bool, tire_buyback: bool):
        self.all_season = all_season_tires
        self.buyback = tire_buyback
        # TODO: W produkcji te zmienne przyjdą z Supabase / reference_data settings
        self.storage_cost_per_month = 20.0
        self.swap_cost_per_season = (
            150.0  # W sezonowych x2, w wielosezonowych co dystans
        )
        self.tire_set_price = 1500.0
        self.buyback_value = 200.0

    def calculate_cost(self, months: int, total_km: int) -> Dict[str, Any]:
        """Kalkuluje techniczne koszty opon (stałe i zmienne) dla danego wariantu."""
        storage_total = 0.0
        swaps_total = 0.0
        sets_needed = 1  # Standardowy z fabryki

        # Schodkowa logika ilości kompletów
        if total_km > 60000:
            sets_needed = 2
        if total_km > 120000:
            sets_needed = 3
        if total_km > 180000:
            sets_needed = 4

        # Rozdziel i policz dla poszczególnych rodzajów opon
        if self.all_season:
            # Brak storage, ale rotacje + wyważenie co np. 60 tys km
            rotations_required = total_km // 60000
            swaps_total = rotations_required * self.swap_cost_per_season
        else:
            # 2 zmiany na pełny rok + przechowywanie
            years = months / 12.0
            swaps_total = (years * 2) * self.swap_cost_per_season
            storage_total = months * self.storage_cost_per_month

        total_hw_cost = (sets_needed - 1) * self.tire_set_price

        # Opcja odkupu
        discount = 0.0
        if self.buyback:
            discount = self.buyback_value

        monthly_total_cost = (
            (storage_total + swaps_total + total_hw_cost - discount) / months
            if months > 0
            else 0
        )

        return {
            "monthly_storage": storage_total / months if months > 0 else 0,
            "monthly_swaps": swaps_total / months if months > 0 else 0,
            "monthly_hardware": total_hw_cost / months if months > 0 else 0,
            "monthly_discount": discount / months if months > 0 else 0,
            "total_monthly_tire_cost": monthly_total_cost,
            "capex_initial_set": self.tire_set_price,  # Dodawane do sumy finansowanej
            "sets_needed": sets_needed,
        }
