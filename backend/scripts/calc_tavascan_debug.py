import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath("."))
from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input
from core.LTRKalkulator import LTRKalkulator

async def main():
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    print("\n--- Vehicle: SWNLCDYR (Tavascan) ---")
    v_res = (
        supabase.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .ilike("synthesis_data->>configuration_code", "%SWNLCDYR%")
        .execute()
    )
    if not v_res.data:
        print("Not found")
        return

    vehicle_row = v_res.data[0]
    
    # Check the data in vehicle_row
    print(f"Base from top: {vehicle_row.get('base_price')}")
    print(f"Total from top: {vehicle_row.get('total_price')}")
    print(f"Factory options from top: {vehicle_row.get('factory_options')}")
    
    synth_data = vehicle_row.get("synthesis_data", {})
    card_sum = synth_data.get("card_summary", {})
    print(f"synth -> card_summary: {json.dumps(card_sum, ensure_ascii=False, indent=2)}")

    base_input = build_calculator_input(vehicle_row, 0.15, settings) # forced 15% discount for testing, but let's see what is inside
    
    print(f"Base Input built. Pricing_margin_pct: {base_input.financial_params.pricing_margin_pct}")
    print(f"Base Input built. base_price_net: {base_input.catalog_base_price_net}")
    print(f"Base Input built. factory_options: {base_input.factory_options}")
    print(f"Base Input built. sales_prep: {base_input.financial_params.sales_prep_correction}")
    print(f"Base Input built. discount_pct: {base_input.financial_params.discount_pct}")

    engine = LTRKalkulator(input_data=base_input, settings=settings)
    res = engine.build_matrix()

    print("\n--- Result for 48m, 15000km/yr ---")
    if res:
        for cell in res:
            if cell.get("Okres") == 48 and cell.get("Przebieg") == 15000:
                for k, v in cell.items():
                    print(f"{k}: {v}")
    else:
        print("No result")

asyncio.run(main())
