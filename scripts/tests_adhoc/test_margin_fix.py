from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import (
    build_calculator_input,
    refresh_matrix_cache_for_vehicles,
)
from core.LTRKalkulator import LTRKalkulator

import warnings

warnings.filterwarnings("ignore")


def main():
    print("Testing vehicle CXY6G6NG by explicit ID...")
    vid = "4efad866-2b72-4dca-a5bd-dc7f857c1443"
    try:
        v_res = supabase.table("vehicle_synthesis").select("*").eq("id", vid).execute()
        if not v_res.data:
            print(f"Vehicle {vid} not found.")
            return
    except Exception as e:
        print(f"ERROR fetching vehicle: {e}")
        return

    print("Forcing cache refresh...")
    refresh_matrix_cache_for_vehicles([vid])

    print("Reading from Cache...")
    cache_res = (
        supabase.table("vehicle_matrix_cache")
        .select("*")
        .eq("vehicle_id", vid)
        .eq("duration_months", 48)
        .eq("annual_mileage", 25000)
        .order("monthly_price_net")
        .limit(1)
        .execute()
    )
    c_row = cache_res.data[0]
    cache_base_price = c_row["monthly_price_net"]

    margin_pct = 15.0
    margin_val = margin_pct / 100.0
    reverse_search_raw = cache_base_price / (1.0 - margin_val)
    reverse_search_final = round(reverse_search_raw, 0)
    print("\n--- REVERSE SEARCH (Cache + Frontend Math) ---")
    print(f"Base price from DB Cache (0% margin): {cache_base_price:.2f} PLN")
    print(f"Final Cart Price (15% margin, rounded): {reverse_search_final:.2f} PLN")

    cc = supabase.table("control_center").select("*").eq("id", 1).execute().data[0]
    settings = ControlCenterSettings(**cc)

    calc_input = build_calculator_input(
        v_res.data[0], margin_pct=0.0, settings=settings
    )
    engine_0 = LTRKalkulator(
        input_data=calc_input, settings=settings, trace_id="TEST-0"
    )
    cells_0 = engine_0.build_matrix()
    live_p0 = 0
    for cell in cells_0:
        if cell["Okres"] == 48 and cell["Przebieg"] == 25000:
            live_p0 = float(cell["LacznaStawka"])
            break

    calc_input.pricing_margin_pct = 15.0
    engine_15 = LTRKalkulator(
        input_data=calc_input, settings=settings, trace_id="TEST-15"
    )
    cells_15 = engine_15.build_matrix()
    live_p15 = 0
    for cell in cells_15:
        if cell["Okres"] == 48 and cell["Przebieg"] == 25000:
            live_p15 = float(cell["LacznaStawka"])
            break

    print("\n--- VERTEX EXTRACTOR (Live LTRKalkulator) ---")
    print(f"Live Price (0% margin): {live_p0:.2f} PLN")
    print(f"Live Price (15% margin): {live_p15:.2f} PLN")

    print("\n--- COMPARISON ---")
    d0 = abs(cache_base_price - live_p0)
    d15 = abs(reverse_search_final - live_p15)
    print(f"Diff at 0% margin: {d0:.2f} PLN")
    print(f"Diff at 15% margin: {d15:.2f} PLN")
    if d0 < 1 and d15 < 1:
        print("\nOK PARITY ACHIEVED! Prices perfectly match.")
    else:
        print("\nFAIL MISMATCH!")


if __name__ == "__main__":
    main()
