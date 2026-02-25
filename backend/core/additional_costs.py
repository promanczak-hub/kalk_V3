from typing import Any, Dict


class AdditionalCostsCalculator:
    """Moduł odpowiedzialny za ryczałtowe koszty dodawane do bazy netto z zakładki 'Koszty Dodatkowe' (V1 LTR)"""

    def __init__(self, settings: Any, input_data: Any, months: int):
        self.settings = settings
        self.input_data = input_data
        self.months = months

    def calculate_cost(self) -> Dict[str, Any]:
        total = 0.0

        # GSM Subscription & Device
        if self.input_data.add_gsm_subscription:
            abonament = self.settings.cost_gsm_subscription_monthly * self.months
            urzadzenie = self.settings.cost_gsm_device / 6.0 * (self.months / 12.0)
            montaz = self.settings.cost_gsm_installation
            total += abonament + urzadzenie + montaz

        # Hak
        if self.input_data.add_hook_installation:
            total += self.settings.cost_hook_installation

        # Krata
        if self.input_data.add_grid_dismantling:
            total += self.settings.cost_grid_dismantling

        # Rejestracja / Karta
        if self.input_data.add_registration:
            total += self.settings.cost_registration

        # Przygotowanie do Sprzedaży (Liniowo, V1 czasami mnożyło to przez korekty z SAMAR, ale spłaszczamy wg założeń ryczałtowych)
        if self.input_data.add_sales_prep:
            total += self.settings.cost_sales_prep

        return {
            "total_additional_costs": round(total, 2),
            "monthly_additional_costs": round(total / self.months, 2)
            if self.months > 0
            else 0.0,
        }
