import asyncio
import json
from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input
from core.LTRKalkulator import LTRKalkulator

async def main():
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    vid = '158e4de0-e3c9-488f-b224-676be5659a5d'
    
    v_res = supabase.table("vehicle_synthesis").select("id, synthesis_data").eq("id", vid).execute()
    vehicle_row = v_res.data[0]
    
    # calculate with 0% margin
    base_input = build_calculator_input(vehicle_row, 0.0, settings)
    
    calc_input = base_input.model_copy()
    calc_input.pricing_margin_pct = 0.0
    calc_input.okres_bazowy = 48
    calc_input.przebieg_bazowy = 60000
    
    engine = LTRKalkulator(input_data=calc_input, settings=settings)
    matrix = engine.build_matrix()
    
    for cell in matrix:
        if cell.get("Okres") == 48 and cell.get("Przebieg") == 15000:
            print(json.dumps(cell, indent=2))

asyncio.run(main())
