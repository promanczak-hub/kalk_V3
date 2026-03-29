import os
import time
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not key:
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

try:
    print("Fetching up to 1000 vehicle IDs from DB...")
    res = (
        supabase.table("vehicle_matrix_cache")
        .select("vehicle_id")
        .limit(1000)
        .execute()
    )
    v_ids = [r["vehicle_id"] for r in res.data]
    print(f"Found {len(v_ids)} IDs.")

    print(f"Executing rpc_get_similar_vehicles_batch with {len(v_ids)} IDs...")
    t0 = time.time()
    r = supabase.rpc(
        "rpc_get_similar_vehicles_batch",
        {
            "p_vehicle_ids": v_ids,
            "p_limit": 5,
            "p_duration_months": 36,
            "p_annual_mileage": 20000,
        },
    ).execute()
    t1 = time.time()

    print(f"SUCCESS in {t1 - t0:.2f} seconds")
    print("Returned rows:", len(r.data))
except Exception:
    print("ERROR:")
    import traceback

    traceback.print_exc()
