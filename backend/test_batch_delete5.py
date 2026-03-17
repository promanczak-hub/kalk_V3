import requests
import os
import sys

# add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import supabase

try:
    print("Fetching two vehicles to delete...")
    res = supabase.table("vehicle_synthesis").select("id").limit(2).execute()
    if not res.data or len(res.data) < 2:
        print("Not enough vehicles")
        sys.exit(0)
    
    vehicle_ids = [v["id"] for v in res.data]
    print(f"HTTP deleting vehicles {vehicle_ids}...")
    
    url = "http://localhost:8000/api/delete-vehicles-batch"
    response = requests.post(url, json={"vehicle_ids": vehicle_ids})
    
    print(f"Status: {response.status_code}")
    print(f"Text: {response.text}")
    print(f"Headers: {response.headers}")

except Exception:
    import traceback
    traceback.print_exc()
