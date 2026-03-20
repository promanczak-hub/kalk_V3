import asyncio
import sys
import os

from pprint import pprint

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

    # Let's see what build_calculator_input returns!
    base_input = build_calculator_input(vehicle_row, 0.15, settings)
    if not base_input:
        print("Failed to build input")
        return

    print("--- LTRInputData ---")
    pprint(base_input.model_dump())

    engine = LTRKalkulator(input_data=base_input, settings=settings)
    res = engine.build_matrix()

    print("\n--- Result for 48m, 15000km/yr ---")
    if res:
        for cell in res:
            if cell.get("Okres") == 48 and cell.get("Przebieg") == 15000:
                pprint(cell)
    else:
        print("No result")

asyncio.run(main())
