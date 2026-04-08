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
    vid = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vid)
        .execute()
    )
    vehicle = res.data[0]

    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**settings_res.data[0])

    calc_input = build_calculator_input(vehicle, 0.0)
    calc_input.wibor_pct = 5.85
    calc_input.margin_pct = 2.0
    calc_input.z_oponami = True  # We want the 2829 one
    calc_input.okres_bazowy = 48
    calc_input.przebieg_bazowy = 40000

    engine = LTRKalkulator(input_data=calc_input, settings=settings)
    matrix = engine.build_matrix()

    for cell in matrix:
        if int(cell["Okres"]) == 48 and int(cell["Przebieg"]) == 10000:
            print(f"LIVE PRICE (48m/10k): {cell['LacznaStawka']} PLN")
            # The matrix cell doesn't have the trace, we need to run a single calc if possible
            # But build_matrix doesn't return traces.
            # Let's look at LTRKalkulator.py to see how to get detailed results.
            break


if __name__ == "__main__":
    asyncio.run(verify())
