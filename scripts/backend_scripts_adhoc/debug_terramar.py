import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(r"D:\kalk_v3\frontend\.env.local")
url = os.environ.get("VITE_SUPABASE_URL")
key = os.environ.get("VITE_SUPABASE_ANON_KEY")

supabase = create_client(url, key)
response = (
    supabase.table("vehicle_synthesis")
    .select("synthesis_data")
    .order("created_at", desc=True)
    .limit(1)
    .execute()
)

data = response.data[0]["synthesis_data"]
with open("terramar_debug.json", "w", encoding="utf-8") as f:
    json.dump(data.get("card_summary", {}), f, indent=2, ensure_ascii=False)
print("Saved to terramar_debug.json")
