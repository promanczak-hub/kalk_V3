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
        budzet_marketingowy_ltr = 0.005

    settings = MockSettings()

    print("Inspecting LTRKalkulator...")
    try:
        calc = LTRKalkulator(calc_input, settings)
        print("Methods in LTRKalkulator:")
        for attr in dir(calc):
            if not attr.startswith("_"):
                print(f" - {attr}")

        # Let's try to find if it has run_pipeline or calculate
        if hasattr(calc, "run_pipeline"):
            print("Found run_pipeline!")
        if hasattr(calc, "calculate"):
            print("Found calculate!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    simulate_skoda_calc()
