import asyncio
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup environment
load_dotenv(".env")
url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
supabase: Client = create_client(url, key)


async def test_calc():
    print("Testing calc directly from DB payload...")
    res = (
        supabase.table("ltr_kalkulacje")
        .select("stan_json")
        .eq("id", "84f2185b-2ca7-4181-8e20-57f077dc0ca0")
        .limit(1)
        .execute()
    )
    if not res.data:
        print("Not found.")
        return

    payload = res.data[0]["stan_json"]

    # Run calculating pipeline manually or call the recalculation endpoint logic
    # Actually, we can just use debug_pipeline.py which does exactly this!
    print("Writing to debug_pipeline2.py")


if __name__ == "__main__":
    asyncio.run(test_calc())
