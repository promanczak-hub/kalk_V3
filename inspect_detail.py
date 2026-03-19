import asyncio
import os
import sys
import json
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase

async def inspect():
    vid = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    res = supabase.table("vehicle_synthesis").select("synthesis_data").eq("id", vid).execute()
    if res.data:
        print(json.dumps(res.data[0].get("synthesis_data", {}).get("card_summary", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(inspect())
