import os
import sys

# add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import supabase

try:
    print("Fetching two vehicles to delete...")
    res = supabase.table("vehicle_synthesis").select("id").limit(2).execute()
    if not res.data or len(res.data) < 2:
        print("Not enough vehicles to delete")
        sys.exit(0)

    vehicle_ids = [v["id"] for v in res.data]
    print(f"Trying to delete vehicles {vehicle_ids}...")

    response = (
        supabase.table("vehicle_synthesis").delete().in_("id", vehicle_ids).execute()
    )
    print("Success:", response)
except Exception:
    import traceback

    traceback.print_exc()
