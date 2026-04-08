import sys
import os
from unittest.mock import MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "backend"))

# Mocking core.database before any imports
mock_db = MagicMock()
sys.modules["core.database"] = mock_db
sys.modules["backend.core.database"] = mock_db

from api.schemas.calculator import CalculatorInput, VehicleOptions
from backend.core.LTRKalkulator import LTRKalkulator


# Create a "Safe" version of the calculator for simulation
class SafeLTRKalkulator(LTRKalkulator):
    def build_matrix(self, only_exact=False):
        calc_input = self.input_data
        settings = self.settings

        # Prices
        base_price_net = calc_input.base_price_net
        discount_pct = calc_input.discount_pct / 100.0

        total_options_net = sum(opt.price_net for opt in calc_input.factory_options)

        # Scenario A: Discount applies to TOTAL (Base + Options) - Current logic
        capex_scenario_a = (base_price_net + total_options_net) * (1 - discount_pct)

        # Scenario B: Discount applies ONLY to Base Price
        capex_scenario_b = (base_price_net * (1 - discount_pct)) + total_options_net

        # WR Calculation: 40% as RESIDUAL PERCENTAGE for Base, 21% for Options
        # Target: 84,477.00
        wr_base_multiplier = 0.40
        wr_options_multiplier = 0.21

        # WR = (BaseNet * 0.40) + (OptionsNet * 0.21)
        wr_total_net = (base_price_net * wr_base_multiplier) + (
            total_options_net * wr_options_multiplier
        )

        print("\n--- SKODA SUPERB CALIBRATION (Row 1679) ---")
        print(f"Base Price Net: {base_price_net:,.2f}")
        print(f"Options Net: {total_options_net:,.2f}")
        print(f"Discount: {calc_input.discount_pct}%")
        print("-" * 30)
        print(f"CAPEX Scenario A (Discount Total): {capex_scenario_a:,.2f}")  # ~174k
        print(
            f"CAPEX Scenario B (Discount Base Only): {capex_scenario_b:,.2f}"
        )  # ~181k
        print("-" * 30)
        print(f"Computed WR (net) [40% WR base / 21% WR options]: {wr_total_net:,.2f}")
        print("Target WR (net): 84,477.00")
        print(f"Difference: {wr_total_net - 84477.00:,.2f}")

        # Let's check if 40% 21% was the intention
        # 201504 * 0.40 = 80601
        # 28211 * 0.21 = 5924
        # Sum = 86525 (Very close to 84477!)

        # If we include -1% color correction:
        # WR = (Base * (0.40 - 0.01)) + (Options * 0.21)
        wr_with_color = (base_price_net * 0.39) + (total_options_net * 0.21)
        print(f"WR with -1% Color Correction (39% base): {wr_with_color:,.2f}")
        print(f"Difference with color: {wr_with_color - 84477.00:,.2f}")

        return [{"CenaZakupu": capex_scenario_a, "WR": wr_total_net}]


def simulate_skoda_calc():
    factory_options = [
        VehicleOptions(
            name="Options Total",
            price_net=28211.38,
            price_gross=34700.0,
            include_in_wr=True,
        )
    ]

    calc_input = CalculatorInput(
        vehicle_id="skoda-1679",
        base_price_net=201504.07,
        discount_pct=24.0,
        factory_options=factory_options,
        service_options=[],
        pricing_margin_pct=0.0,
        margin_pct=2.2,
        wibor_pct=3.83,
        matrix_km_mode="annual",
        okres_bazowy=48,
        przebieg_bazowy=140000,
        z_oponami=False,
        klasa_opony_string="Medium",
        srednica_felgi=19,
        include_servicing=False,
        replacement_car_enabled=False,
        add_hook_installation=False,
        is_metalic=True,
    )

    class MockSettings:
        bank_spread = 2.2
        default_wibor = 3.83
        vat_rate = 1.23
        normatywny_przebieg_mc = 1667

    settings = MockSettings()

    calc = SafeLTRKalkulator(calc_input, settings)
    calc.build_matrix(only_exact=True)


if __name__ == "__main__":
    simulate_skoda_calc()
