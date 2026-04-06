import asyncio
import os
import sys
import json
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input
from api.schemas.calculator import CalculatorInput

async def verify():
    vid = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").eq("id", vid).execute()
    vehicle = res.data[0]
    
    cache_res = supabase.table("vehicle_matrix_cache").select("*").eq("vehicle_id", vid).eq("margin_pct", 0.0).eq("duration_months", 12).eq("annual_mileage", 10000).execute()
    cache_price = cache_res.data[0]["monthly_price_net"]
    print(f"CACHE PRICE (12m/10k): {cache_price} PLN")

    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])
    
    # Test different scenarios
    scenarios = [
        {"name": "Full (Normal)", "include_servicing": True, "z_oponami": True, "replacement_car_enabled": True},
        {"name": "No Tires", "include_servicing": True, "z_oponami": False, "replacement_car_enabled": True},
        {"name": "No Service", "include_servicing": False, "z_oponami": True, "replacement_car_enabled": True},
        {"name": "No RC", "include_servicing": True, "z_oponami": True, "replacement_car_enabled": False},
        {"name": "Bare (No Service/Tires/RC)", "include_servicing": False, "z_oponami": False, "replacement_car_enabled": False},
    ]

    for sc in scenarios:
        calc_input = build_calculator_input(vehicle, 0.0)
        calc_input.wibor_pct = 5.85
        calc_input.margin_pct = 2.0
        calc_input.include_servicing = sc["include_servicing"]
        calc_input.z_oponami = sc["z_oponami"]
        calc_input.replacement_car_enabled = sc["replacement_car_enabled"]
        calc_input.okres_bazowy = 12
        calc_input.przebieg_bazowy = int(round((10000 / 12) * 12))
        
        engine = LTRKalkulator(input_data=calc_input, settings=settings)
        matrix = engine.build_matrix()
        
        live_price = None
        for cell in matrix:
            if int(cell["Okres"]) == 12 and int(cell["Przebieg"]) == 10000:
                live_price = float(cell["LacznaStawka"])
                break
        
        diff = abs(live_price - cache_price)
        print(f"SCENARIO: {sc['name']} -> Live: {live_price} | Diff: {diff:.2f}")

if __name__ == "__main__":
    asyncio.run(verify())
