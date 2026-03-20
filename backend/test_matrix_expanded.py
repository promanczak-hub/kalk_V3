import logging
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    # Weź jedno auto które MA cache (żebyśmy mogli porównać)
    res_cache = (
        supabase.table("vehicle_matrix_cache").select("vehicle_id").limit(1).execute()
    )
    if res_cache.data:
        vid = res_cache.data[0]["vehicle_id"]
        print(f"Testing full refresh for vehicle: {vid}")

        # Przed
        before = (
            supabase.table("vehicle_matrix_cache")
            .select("annual_mileage")
            .eq("vehicle_id", vid)
            .execute()
        )
        before_mileages = sorted(set(r["annual_mileage"] for r in (before.data or [])))
        print(f"BEFORE mileages: {before_mileages}")

        # Refresh
        refresh_matrix_cache_for_vehicles([vid])

        # Po
        after = (
            supabase.table("vehicle_matrix_cache")
            .select("annual_mileage")
            .eq("vehicle_id", vid)
            .execute()
        )
        after_mileages = sorted(set(r["annual_mileage"] for r in (after.data or [])))
        print(f"AFTER mileages: {after_mileages}")
        print(f"NEW mileages added: {set(after_mileages) - set(before_mileages)}")
    else:
        print("No cached vehicles found!")
