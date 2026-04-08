import asyncio
from dotenv import load_dotenv

load_dotenv(r"d:\kalk_v3\backend\.env")

import sys

sys.path.append(r"d:\kalk_v3\backend")

from core.database import supabase
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew


async def verify():
    # just get all vehicles and filter
    res = supabase.table("samar_data").select("*").limit(1).execute()
    # We will just construct vehicle manually to test the SAMAR algorithm
    # since we know it's a Skoda Superb, D classification, ON (Diesel).

    # We need the correct params:
    # Marka = Skoda
    # Klasa = D
    # Fuel = ON (ID: 3 in some mappings, let's say Diesel)

    # We can do this through LTRSubCalculatorUtrataWartosciNew without build_calculator_input if we mock calc_input.
    # Actually, we can fetch the exact samar_data row for "CJYHGY2X", wait "CJYHGY2X" might not exist because it's not in the DB?
    # Let's search samar_data by ID "CJYHGY2X" or similar. But earlier I saw "Could not find table public.samar_data".

    # Let's see what tables exist locally.
    tbls = supabase.table("samar_classes").select("id, name").execute()
    kelas_id = next((x["id"] for x in tbls.data if x["name"] == "D"), None)

    if not kelas_id:
        print("Cannot find class D")
        return

    class MockData:
        samar_class_id = kelas_id
        engine_id = 3  # Diesel (Usually 3 = ON)
        brand = "SKODA"
        model = "Superb"
        vehicle_body = "ND"
        paint_type = "niemetalik"
        manual_wr_correction = 0.0
        vintage_year = 2026  # bieżący

    base_gross = 247850.0
    options_gross = 34500.0
    months = 48
    total_km = 140000

    calc = LTRSubCalculatorUtrataWartosciNew(
        data=MockData(),
        months=months,
        kilometers_total=total_km,
        base_vehicle_capex_gross=base_gross,
        options_capex_gross=options_gross,
    )

    out = calc.calculate_values()
    print("WR Brutto V3:", out["WR_Gross"])
    print("WR Netto V3:", out["WR"])
    for t in out.get("Trace", []):
        print(t)


asyncio.run(verify())
