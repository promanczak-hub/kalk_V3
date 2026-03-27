import asyncio
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Modify path to allow importing from backend
import os

sys.path.append(os.path.abspath("d:/kalk_v3/backend"))

from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input
from api.schemas.calculator import CalculatorInput
from typing import cast


async def compare(vehicle_id: str):
    print(f"Comparing inputs for vehicle: {vehicle_id}")

    # 1. Fetch from vehicle_synthesis
    v_res = (
        supabase.table("vehicle_synthesis").select("*").eq("id", vehicle_id).execute()
    )
    if not v_res.data:
        print("Vehicle not found in vehicle_synthesis")
        return
    vehicle_row = v_res.data[0]

    # 2. Fetch CC settings
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings_dict = cast(dict, settings_res.data[0])
    settings = ControlCenterSettings(**settings_dict)

    # 3. Build input from synthesis (cache way)
    calc_input_cache = build_calculator_input(
        vehicle_row, margin_pct=0.0, settings=settings
    )

    # 4. Fetch from ltr_kalkulacje (Vertex way) - GET LATEST
    k_res = (
        supabase.table("ltr_kalkulacje")
        .select("*")
        .eq("stan_json->>vehicle_id", vehicle_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not k_res.data:
        print("No kalkulacja found for this vehicle")
        return
    kalk_row = k_res.data[0]
    stan_json = kalk_row.get("stan_json") or {}
    print(
        f"Found latest kalkulacja: {kalk_row['id']} (created_at: {kalk_row['created_at']})"
    )

    try:
        calc_input_vertex = CalculatorInput(**stan_json)
    except Exception as e:
        print(f"Error parsing stan_json: {e}")
        return

    # 5. Compare the two
    cache_dict = calc_input_cache.model_dump()
    vertex_dict = calc_input_vertex.model_dump()

    differences = {}
    for key, cache_val in cache_dict.items():
        vertex_val = vertex_dict.get(key)
        if cache_val != vertex_val:
            differences[key] = {
                "cache_builder": cache_val,
                "vertex_stan_json": vertex_val,
            }

    print("\n--- DIFFERENCES ---")
    if not differences:
        print("NO DIFFERENCES FOUND! They are identical.")
    else:
        for k, v in differences.items():
            print(f"\nField: {k}")
            print(f"  Cache builder : {v['cache_builder']}")
            print(f"  Vertex        : {v['vertex_stan_json']}")


if __name__ == "__main__":
    vid = "749333ec-06be-4913-be43-fb7895f559bb"
    asyncio.run(compare(vid))
