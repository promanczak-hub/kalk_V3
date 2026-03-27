import logging
import traceback
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.INFO)


def main():
    print("Fetching all vehicle IDs from vehicle_synthesis...")
    res = supabase.table("vehicle_synthesis").select("id").execute()
    all_ids = [v["id"] for v in res.data]
    print(f"Total vehicles to refresh: {len(all_ids)}")

    try:
        refresh_matrix_cache_for_vehicles(all_ids)
    except Exception:
        print("An error occurred during global refresh:")
        traceback.print_exc()

    print(
        "Job dispatch completed. Check celery output/logs for exact generation status."
    )


if __name__ == "__main__":
    main()
