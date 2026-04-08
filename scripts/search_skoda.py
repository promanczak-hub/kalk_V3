import asyncio
from dotenv import load_dotenv
import json

load_dotenv(r"d:\kalk_v3\backend\.env")

import sys

sys.path.append(r"d:\kalk_v3\backend")

from core.database import supabase


async def verify():
    all_data = []
    start = 0
    while True:
        res = (
            supabase.table("vehicle_synthesis")
            .select("id, synthesis_data")
            .range(start, start + 999)
            .execute()
        )
        if not res.data:
            break
        all_data.extend(res.data)
        start += 1000

    print(f"Total vehicles: {len(all_data)}")
    for item in all_data:
        try:
            if isinstance(item.get("synthesis_data"), str):
                sd = json.loads(item["synthesis_data"])
            else:
                sd = item.get("synthesis_data") or {}

            p_id = sd.get("pojazd", {}).get("id")
            if p_id == "CJYHGY2X":
                print("Found!", item["id"])
                with open("trace_skoda.py", "w", encoding="utf-8") as f:
                    f.write(f'''
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv(r"d:\\kalk_v3\\backend\\.env")

import sys
sys.path.append(r"d:\\kalk_v3\\backend")

from core.database import supabase
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew
from core.models import ControlCenterSettings
from core.matrix_cache_job import build_calculator_input

async def calc():
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").eq("id", "{item["id"]}").execute()
    car = res.data[0]
    
    sd = car.get("synthesis_data")
    if isinstance(sd, str):
        sd = json.loads(sd)
    car["synthesis_data"] = sd
    
    calc_input = build_calculator_input(car, 0.0)
    
    base_gross = 247850.0
    options_gross = 34500.0
    months = 36
    total_km = 150000
    
    calc = LTRSubCalculatorUtrataWartosciNew(
        data=calc_input,
        months=months,
        kilometers_total=total_km,
        base_vehicle_capex_gross=base_gross,
        options_capex_gross=options_gross
    )
    
    out = calc.calculate_values()
    print("WR Brutto V3:", out["WR_Gross"])
    for t in out.get("Trace", []):
        print(t)

asyncio.run(calc())
''')
                return
        except Exception:
            pass
    print("Not found CJYHGY2X in synthesis_data.pojazd.id")


asyncio.run(verify())
