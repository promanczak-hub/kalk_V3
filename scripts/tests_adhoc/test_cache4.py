import asyncio
from core.database import supabase


async def main():
    vehicles = [
        "158e4de0-e3c9-488f-b224-676be5659a5d",
        "a6d6ff54-1dbb-4bb4-905e-71fcc240083a",
    ]
    for vid in vehicles:
        print(f"\nVehicle: {vid}")
        res = (
            supabase.table("vehicle_matrix_cache")
            .select("monthly_price_net")
            .eq("vehicle_id", vid)
            .execute()
        )
        if res.data:
            min_price = min(
                (
                    float(r["monthly_price_net"])
                    for r in res.data
                    if r["monthly_price_net"]
                )
            )
            print(f"  Min Price: {min_price}")
            print(f"  Search UI equivalent with 14% margin: {min_price / 0.86}")
        else:
            print("  No cache")


asyncio.run(main())
