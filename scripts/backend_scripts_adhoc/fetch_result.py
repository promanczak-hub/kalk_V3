import os
import time
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

url = os.environ.get("VITE_SUPABASE_URL")
key = os.environ.get("VITE_SUPABASE_ANON_KEY")
supabase = create_client(url, key)

file_id = "5b85bdb6-e2ba-4c73-a9b2-3d5ac3237388"

for _ in range(30):  # wait up to 60s
    res = (
        supabase.table("vehicle_synthesis")
        .select("verification_status, synthesis_data")
        .eq("id", file_id)
        .execute()
    )
    data = res.data
    if data:
        status = data[0].get("verification_status")
        print(f"Status: {status}")
        if status != "processing":
            import json

            with open("bmw_3_result.json", "w", encoding="utf-8") as f:
                json.dump(
                    data[0].get("synthesis_data"), f, indent=2, ensure_ascii=False
                )
            print("DATA saved to bmw_3_result.json")
            break
    else:
        print("Not found yet...")
    time.sleep(2)
