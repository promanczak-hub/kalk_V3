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
    print(f"Testing Vehicle: {vid}")
    
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").eq("id", vid).execute()
    if not res.data:
        print("Vehicle not found.")
        return
    vehicle = res.data[0]
    
    # 1. Check Cache
    print("\nChecking vehicle_matrix_cache...")
    cache_res = supabase.table("vehicle_matrix_cache").select("*").eq("vehicle_id", vid).eq("margin_pct", 0.0).limit(5).execute()
    if not cache_res.data:
        print("No cache found with margin 0.0.")
        return
    
    # Let's test all variants in cache
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])
    
    calc_input = build_calculator_input(vehicle, 0.0)
    # Match matrix_cache_job.py defaults
    calc_input.wibor_pct = 5.85
    calc_input.margin_pct = 2.0
    
    print(f"Base Total Price (Net): {calc_input.base_price_net} PLN")
    
    engine = LTRKalkulator(input_data=calc_input, settings=settings)
    matrix = engine.build_matrix()
    
    print("\nComparing Cache vs Live (Margin 0.0%):")
    matches = 0
    total = 0
    for cache_entry in cache_res.data:
        months = cache_entry["duration_months"]
        mileage = cache_entry["annual_mileage"]
        cache_price = cache_entry["monthly_price_net"]
        
        live_price = None
        for cell in matrix:
            if int(cell["Okres"]) == months and int(cell["Przebieg"]) == mileage:
                live_price = float(cell["LacznaStawka"])
                break
        
        if live_price is not None:
            total += 1
            diff = abs(live_price - cache_price)
            status = "✅" if diff < 1.0 else "❌"
            if diff < 1.0: matches += 1
            print(f"[{months}m / {mileage}km] Cache: {cache_price} | Live: {live_price} | Diff: {diff:.2f} | {status}")
        else:
            print(f"[{months}m / {mileage}km] Live calculation missing for this pair.")

    if total > 0:
        print(f"\nResult: {matches}/{total} matches.")
    else:
        print("\nNo overlapping data found to compare.")

if __name__ == "__main__":
    asyncio.run(verify())
