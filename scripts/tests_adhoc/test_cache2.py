import asyncio
from core.database import supabase


async def main():
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, samar_id")
        .eq("samar_id", "C9DQAAPO")
        .execute()
    )
    vehicles = res.data
    for v in vehicles:
        print(f"Vehicle: {v['id']} {v['brand']} {v['model']} {v['samar_id']}")

        cache_0 = (
            supabase.table("vehicle_matrix_cache")
            .select("*")
            .eq("vehicle_id", v["id"])
            .eq("margin_pct", 0)
            .eq("duration_months", 48)
            .eq("annual_mileage", 15000)
            .execute()
        )
        if cache_0.data:
            print(
                f"  Cache (0 margin, 48m, 15k): {cache_0.data[0]['monthly_price_net']}"
            )
        else:
            print("  Cache not found for 0 margin, 48m, 15k")

        all_cache = (
            supabase.table("vehicle_matrix_cache")
            .select("margin_pct, duration_months, annual_mileage, monthly_price_net")
            .eq("vehicle_id", v["id"])
            .execute()
        )
        print(f"  Total cache entries: {len(all_cache.data)}")
        for row in all_cache.data[:5]:
            print(f"    {row}")


asyncio.run(main())
