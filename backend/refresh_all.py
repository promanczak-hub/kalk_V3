from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    # Check total vehicles
    res = (
        supabase.table("vehicle_synthesis")
        .select("id")
        .neq("verification_status", "moved_to_library")
        .execute()
    )
    vids = [r["id"] for r in res.data]
    print(f"Total vehicles to refresh: {len(vids)}")

    # Process in small chunks
    chunk_size = 5
    for i in range(0, len(vids), chunk_size):
        chunk = vids[i : i + chunk_size]
        refresh_matrix_cache_for_vehicles(chunk)
        print(f"Processed {min(i + chunk_size, len(vids))}/{len(vids)}")

    print("All vehicles refreshed to 0% margin database.")


if __name__ == "__main__":
    main()
