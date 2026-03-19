import asyncio
from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input
from core.LTRKalkulator import LTRKalkulator

async def main():
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    vehicles = [
        '158e4de0-e3c9-488f-b224-676be5659a5d', # C9DQAAPO
        'a6d6ff54-1dbb-4bb4-905e-71fcc240083a'  # C9DQA4GM
    ]
    
    for vid in vehicles:
        print(f"\n--- Vehicle: {vid} ---")
        v_res = supabase.table("vehicle_synthesis").select("id, synthesis_data").eq("id", vid).execute()
        if not v_res.data:
            print("Not found")
            continue
        vehicle_row = v_res.data[0]
        
        # calculate with 14% margin
        base_input = build_calculator_input(vehicle_row, 0.14, settings)
        if not base_input:
            print("Failed to build input")
            continue
            
        calc_input = base_input.model_copy()
        calc_input.pricing_margin_pct = 0.14
        calc_input.okres_bazowy = 48
        calc_input.przebieg_bazowy = 60000 # 15k * 4
        
        engine = LTRKalkulator(input_data=calc_input, settings=settings)
        matrix = engine.build_matrix()
        
        for cell in matrix:
            if cell.get("Okres") == 48 and cell.get("Przebieg") == 15000:
                print(f"LIVE (14% margin): {cell.get('LacznaStawka')}")
                print(f"   CzynszFinansowy: {cell.get('CzynszFinansowy')}")
                print(f"   CzynszTechniczny: {cell.get('CzynszTechniczny')}")

asyncio.run(main())
