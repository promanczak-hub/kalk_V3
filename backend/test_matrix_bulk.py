from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

def test_bulk():
    print("Fetching missing vehicles...")
    res_all = supabase.table("vehicle_synthesis").select("id").execute()
    all_ids = set(row["id"] for row in (res_all.data or []))
    
    res_cache = supabase.table("vehicle_matrix_cache").select("vehicle_id").execute()
    cached_ids = set(row["vehicle_id"] for row in (res_cache.data or []))
    
    missing_ids = list(all_ids - cached_ids)
    print(f"Missing vehicles: {len(missing_ids)}")
    
    if not missing_ids:
        print("Done")
        return
        
    print("Testing chunk 1 of 5 items...")
    chunk = missing_ids[:5]
    refresh_matrix_cache_for_vehicles(chunk)

if __name__ == "__main__":
    test_bulk()
