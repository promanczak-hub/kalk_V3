import asyncio
import sys
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input


async def verify():
    print("Fetching a verified vehicle with brand/model...")
    # Find a vehicle that has a brand and model and is in the cache
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("verification_status", "completed")
        .not_.is_("synthesis_data->card_summary->brand", "null")
        .limit(10)
        .execute()
    )

    if not res.data:
        print("No suitable verified vehicles found.")
        return

    best_v = None
    for v in res.data:
        vid = v["id"]
        # Check if it has cache
        cache_check = (
            supabase.table("vehicle_matrix_cache")
            .select("id")
            .eq("vehicle_id", vid)
            .limit(1)
            .execute()
        )
        if cache_check.data:
            best_v = v
            break

    if not best_v:
        print("No verified vehicles with cache found.")
        return

    vehicle = best_v
    vid = vehicle["id"]
    cs = vehicle["synthesis_data"]["card_summary"]
    brand = cs.get("brand")
    model = cs.get("model")
    print(f"Testing Vehicle: {brand} {model} ({vid})")

    # 1. Check Cache
    print("\nChecking vehicle_matrix_cache...")
    cache_res = (
        supabase.table("vehicle_matrix_cache")
        .select("*")
        .eq("vehicle_id", vid)
        .eq("margin_pct", 0.0)
        .limit(1)
        .execute()
    )
    if not cache_res.data:
        print("No cache found with margin 0.0.")
        return

    cache_entry = cache_res.data[0]
    months = cache_entry["duration_months"]
    mileage = cache_entry["annual_mileage"]
    cache_price = cache_entry["monthly_price_net"]
    cache_base_price = cache_entry.get("base_price_net")
    print(
        f"Cache Entry: {months} mos, {mileage} km/yr | LTR Price: {cache_price} PLN | Stored Base Price: {cache_base_price} PLN"
    )

    # 2. Run Live Calculator
    print("\nRunning live LTRKalkulator...")
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    calc_input = build_calculator_input(vehicle, 0.0)
    # FORCING MATCH with matrix_cache_job hardcoded values if they differ from settings
    calc_input.wibor_pct = 5.85  # Hardcoded in matrix_cache_job.py:209
    calc_input.margin_pct = 2.0  # Hardcoded in matrix_cache_job.py:208

    print(f"Input Base Price (parsed): {calc_input.base_price_net} PLN")
    print(f"Input WIBOR: {calc_input.wibor_pct}% | Margin: {calc_input.margin_pct}%")

    calc_input.okres_bazowy = months
    calc_input.przebieg_bazowy = int(round((mileage / 12) * months))

    engine = LTRKalkulator(input_data=calc_input, settings=settings)
    matrix = engine.build_matrix()

    live_price = None
    for cell in matrix:
        if int(cell["Okres"]) == months and int(cell["Przebieg"]) == mileage:
            live_price = float(cell["LacznaStawka"])
            break

    print(f"Live Calculated Price: {live_price} PLN")

    if live_price == cache_price:
        print("\n✅ SUCCESS: Parity confirmed!")
    else:
        diff = abs(live_price - cache_price)
        if diff < 1.0:
            print(f"\n✅ SUCCESS (rounding): {diff} PLN diff")
        else:
            print(f"\n❌ DISCREPANCY: {diff} PLN difference found!")


if __name__ == "__main__":
    asyncio.run(verify())
