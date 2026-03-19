import asyncio
import os
import sys
import json
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase

async def inspect():
    print("Listing 20 recent vehicles with synthesis_data...")
    res = supabase.table("vehicle_synthesis")\
        .select("id, synthesis_data, verification_status")\
        .not_.is_("synthesis_data", "null")\
        .order("created_at", desc=True)\
        .limit(20).execute()
    
    if not res.data:
        print("No vehicles with synthesis_data found.")
        return

    for v in res.data:
        if v is None: continue
        vid = v["id"]
        status = v["verification_status"]
        sd = v.get("synthesis_data") or {}
        cs = sd.get("card_summary") or {}
        brand = cs.get("brand")
        model = cs.get("model")
        price = cs.get("total_price")
        print(f"ID: {vid} | Status: {status} | Brand: {brand} | Model: {model} | Price: {price}")

if __name__ == "__main__":
    asyncio.run(inspect())
