import asyncio
from core.database import supabase


async def test():
    # Find a vehicle that has calculations
    try:
        # Get one kalkulacja
        k = supabase.table("kalkulacje").select("vehicle_id").limit(1).execute()
        if k.data and k.data[0].get("vehicle_id"):
            vid = k.data[0]["vehicle_id"]
            print(f"Trying to delete vehicle {vid} which has a kalkulacja...")
            res = supabase.table("vehicle_synthesis").delete().eq("id", vid).execute()
            print("Delete result:", res.data)
        else:
            print("No kalkulacje with vehicle_id found.")
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
