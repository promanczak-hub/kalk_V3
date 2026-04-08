import asyncio
from core.database import supabase
import pandas as pd


async def run():
    # Fetch all vehicle_synthesis IDs
    syn = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, samar_class_id, created_at")
        .execute()
    )
    syn_df = pd.DataFrame(syn.data)
    print(f"Total vehicles in extractor (vehicle_synthesis): {len(syn_df)}")

    # Fetch all distinct vehicles with cache
    # We must paginate or just get all matrix cache rows. Better to get distinct vehicle_ids.
    # Since we can't easily do SELECT DISTINCT in PostgREST, we can get all and then unique in pandas.
    cache = supabase.table("vehicle_matrix_cache").select("vehicle_id").execute()
    cache_df = pd.DataFrame(cache.data)
    unique_cache_vids = cache_df["vehicle_id"].unique() if not cache_df.empty else []
    print(f"Total vehicles with matrix cache: {len(unique_cache_vids)}")

    # 1. Cars in cache but NOT in vehicle_synthesis (Orphaned cache)
    if not cache_df.empty:
        orphaned = set(unique_cache_vids) - set(syn_df["id"])
        print(f"Orphaned cache (in cache but deleted from extractor): {len(orphaned)}")

    # 2. Cars in vehicle_synthesis without cache (Uncalculated)
    uncalculated = syn_df[~syn_df["id"].isin(unique_cache_vids)]
    print(f"\nUncalculated vehicles (in extractor but no cache): {len(uncalculated)}")

    if len(uncalculated) > 0:
        missing_samar = uncalculated[uncalculated["samar_class_id"].isnull()]
        print(f"- Missing SAMAR mapping: {len(missing_samar)}")
        has_samar = uncalculated[uncalculated["samar_class_id"].notnull()]
        print(f"- Has SAMAR mapping but no cache: {len(has_samar)}")

        if len(has_samar) > 0:
            print("\nExamples of 'Has SAMAR but no cache':")
            print(
                has_samar[["id", "brand", "model", "samar_class_id"]]
                .head(15)
                .to_string()
            )


if __name__ == "__main__":
    asyncio.run(run())
