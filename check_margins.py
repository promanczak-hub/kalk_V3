import asyncio
import os
import sys
import json
from pathlib import Path
from collections import Counter

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase

async def inspect():
    vid = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    res = supabase.table("vehicle_matrix_cache").select("*").eq("vehicle_id", vid).execute()
    
    if not res.data:
        print("No cache found for this vehicle.")
        return

    margins = [row["margin_pct"] for row in res.data]
    print(f"Total rows: {len(res.data)}")
    print("Margin distribution:", Counter(margins))

    # Find 12/10000 entries
    for row in res.data:
        if row["duration_months"] == 12 and row["annual_mileage"] == 10000:
            print(f"MATCH: Margin: {row['margin_pct']} | Price: {row['monthly_price_net']} | Base: {row['base_price_net']} | Calculated: {row['calculated_at']}")

if __name__ == "__main__":
    asyncio.run(inspect())
