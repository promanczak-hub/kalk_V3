import asyncio
import sys
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase


async def inspect():
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .not_.is_("synthesis_data", "null")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    if not res.data:
        print("No vehicles found.")
        return

    for v in res.data:
        vid = v["id"]
        cs = v.get("synthesis_data", {}).get("card_summary", {})
        name = cs.get("vehicle_name", "Unknown")
        brand = cs.get("brand")
        model = cs.get("model")
        price = cs.get("total_price")
        print(f"ID: {vid} | Name: {name} | B/M: {brand}/{model} | Price: {price}")


if __name__ == "__main__":
    asyncio.run(inspect())
