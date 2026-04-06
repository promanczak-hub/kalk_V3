import asyncio
import json
from core.database import supabase

async def main():
    resp = supabase.table("vehicle_synthesis").select("synthesis_data").limit(1).execute()
    if resp.data:
        sd = resp.data[0].get("synthesis_data", {})
        cs = sd.get("card_summary", {})
        features = cs.get("features", {})
        print(json.dumps(features, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
