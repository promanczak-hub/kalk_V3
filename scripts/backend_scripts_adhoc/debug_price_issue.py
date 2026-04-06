import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from api.schemas.calculator import CalculatorInput
from core.models import ControlCenterSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_vehicle(vehicle_id: str):
    print(f"\n=== Debugging Vehicle: {vehicle_id} ===")

    # 1. Check vehicle_synthesis
    v_res = (
        supabase.table("vehicle_synthesis").select("*").eq("id", vehicle_id).execute()
    )
    if not v_res.data:
        print(f"ERROR: Vehicle {vehicle_id} not found in vehicle_synthesis")
        return

    row = v_res.data[0]
    sd = row.get("synthesis_data") or {}
    print(f"Synthesis Data Keys: {list(sd.keys())}")

    setup = sd.get("calculator_setup") or {}
    print(f"Calculator Setup Price: {setup.get('catalog_base_price_net')}")

    cs = sd.get("card_summary") or {}
    print(f"Card Summary Price: {cs.get('base_price')}")
    print(f"Card Summary Total Price: {cs.get('total_price')}")
    print(f"Card Summary Price Domain: {cs.get('_price_domain')}")

    # 2. Check CC settings
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    # 3. Test build_calculator_input
    print("\n--- Testing build_calculator_input ---")
    try:
        calc_input = build_calculator_input(row, margin_pct=0.0, settings=settings)
        if calc_input:
            print(
                f"SUCCESS: build_calculator_input returned price: {calc_input.base_price_net}"
            )
        else:
            print("FAILED: build_calculator_input returned None")
    except Exception as e:
        print(f"ERROR in build_calculator_input: {e}")

    # 4. Check existing calculations for this vehicle
    print("\n--- Checking ltr_kalkulacje for this vehicle ---")
    k_res = (
        supabase.table("ltr_kalkulacje")
        .select("*")
        .eq("stan_json->>vehicle_id", vehicle_id)
        .execute()
    )
    if k_res.data:
        for k in k_res.data:
            stan = k.get("stan_json") or {}
            print(
                f"Kalk ID: {k['id']}, Source: {stan.get('source')}, Price in Row: {k.get('cena_netto')}, Price in stan_json: {stan.get('base_price_net')}"
            )
            try:
                CalculatorInput(**stan)
                print("  -> stan_json parses correctly into CalculatorInput")
            except Exception as e:
                print(f"  -> FAILED to parse stan_json: {e}")
    else:
        print("No calculations found in ltr_kalkulacje for this vehicle.")


if __name__ == "__main__":
    # Test the Kodiaq from the screenshot/previous logs
    debug_vehicle("4efad866-2b72-4dca-a5bd-dc7f857c1443")

    # You can add more IDs here if you find them in the failed jobs list
