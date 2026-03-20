import requests
from core.database import supabase

# Get a vehicle ID
res = supabase.table("vehicle_synthesis").select("id, brand, model").limit(5).execute()
if res.data:
    for v in res.data:
        vid = v["id"]
        name = f"{v['brand']} {v['model']}"
        print(f"Testing {name} ({vid}) ...")

        try:
            r1 = requests.get(
                f"http://localhost:8000/api/kalkulator/pojazd/{vid}", timeout=5
            )
            print("  /api/kalkulator STATUS:", r1.status_code)
        except Exception as e:
            print("  /api/kalkulator ERROR:", e)

        try:
            r2 = requests.get(
                f"http://localhost:8000/api/features/vehicle/{vid}/state", timeout=15
            )
            print("  /api/features STATUS:", r2.status_code)
            if r2.status_code != 200:
                print("  Response:", r2.text[:200])
        except Exception as e:
            print("  /api/features ERROR:", e)
