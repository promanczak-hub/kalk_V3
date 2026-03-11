import os
import json
from dotenv import load_dotenv

load_dotenv("backend/.env")
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gnpsdiarmwvqhqbyetce.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

tables = [
    "universal_features",
    "vehicle_feature_state",
    "vehicle_feature_evidence"
]

for table in tables:
    print(f"Backing up {table} via REST API...")
    all_data = []
    page = 0
    page_size = 1000
    
    while True:
        try:
            resp = supabase.schema("reverse_search").table(table).select("*").range(page*page_size, (page+1)*page_size - 1).execute()
            data = resp.data
            if not data:
                break
            all_data.extend(data)
            if len(data) < page_size:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching page {page} for {table}: {e}")
            break
            
    filename = f"d:/kalk_v3/backup_{table}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(all_data)} rows to {filename}")

print("Backup completed.")
