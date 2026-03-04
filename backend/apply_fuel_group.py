"""Check and apply fuel_group_id to engines table."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase

resp = supabase.table("engines").select("*").execute()
has_column = "fuel_group_id" in (resp.data[0] if resp.data else {})

for e in resp.data:
    fgid = e.get("fuel_group_id", "N/A")
    print(f"  {e['id']}: {e['name']} -> fuel_group_id={fgid}")

if has_column:
    print("\nColumn exists. Updating values...")
    mapping = {
        "Benzyna (PB)": 1,
        "Benzyna mHEV (PB-mHEV)": 1,
        "Diesel (ON)": 2,
        "Diesel mHEV (ON-mHEV)": 2,
        "Autogaz (LPG)": 3,
        "Elektryczny (BEV)": 3,
        "Hybryda (HEV)": 3,
        "Hybryda Plug-in (PHEV)": 3,
        "Wodór (FCEV)": 3,
    }
    for name, gid in mapping.items():
        supabase.table("engines").update({"fuel_group_id": gid}).eq(
            "name", name
        ).execute()
        print(f"  Updated {name} -> {gid}")
    print("Done!")
else:
    print("\nColumn fuel_group_id NOT found.")
    print("Run this SQL in Supabase SQL Editor first:")
    print("ALTER TABLE engines ADD COLUMN fuel_group_id INTEGER NOT NULL DEFAULT 1;")
