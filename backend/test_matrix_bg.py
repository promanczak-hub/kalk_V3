import logging
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    # Znajdzmy auto ktorego nie ma w cache
    res_all = supabase.table("vehicle_synthesis").select("id").execute()
    all_ids = set(row["id"] for row in (res_all.data or []))

    res_cache = supabase.table("vehicle_matrix_cache").select("vehicle_id").execute()
    cached_ids = set(row["vehicle_id"] for row in (res_cache.data or []))

    missing_ids = list(all_ids - cached_ids)
    if not missing_ids:
        print("Nie ma aut do przeliczenia")
    else:
        vid = missing_ids[0]
        print(f"Test dla id: {vid}")
        refresh_matrix_cache_for_vehicles([vid])
