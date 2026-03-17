import os
import sys

# add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import supabase

try:
    print("Fetching one vehicle to delete...")
    res = supabase.table("vehicle_synthesis").select("id").limit(1).execute()
    if not res.data:
        print("No vehicles to delete")
        sys.exit(0)
    
    vehicle_id = res.data[0]["id"]
    print(f"Trying to delete vehicle {vehicle_id}...")
    
    response = supabase.table("vehicle_synthesis").delete().in_(
        "id", [vehicle_id]
    ).execute()
    print("Success:", response)
except Exception:
    import traceback
    traceback.print_exc()
