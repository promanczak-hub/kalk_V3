import time
import sys

# Add backend directory to path so imports work
sys.path.append("/app")

try:
    from core.database import supabase

    print("Testing Supabase Latency...")
    # Test Read
    start = time.time()
    res = supabase.table("vehicle_synthesis").select("brand").limit(1).execute()
    read_time = time.time() - start
    print(f"Read Time: {read_time:.4f}s")

    # Test file_hash read latency
    start = time.time()
    res = (
        supabase.table("vehicle_synthesis")
        .select("brand")
        .eq("file_hash", "dummy_hash123")
        .execute()
    )
    hash_read_time = time.time() - start
    print(f"Hash Query Time: {hash_read_time:.4f}s")

except Exception as e:
    print(f"Error: {e}")
