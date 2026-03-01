import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

supabase_url = os.environ.get("VITE_SUPABASE_URL")
supabase_key = os.environ.get("VITE_SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    pass

supabase: Client = create_client(supabase_url, supabase_key)

response = (
    supabase.table("vehicle_synthesis")
    .select("synthesis_data")
    .eq("id", "0e34c506-f53a-4818-8f0f-e7b72301c25a")
    .execute()
)
if response.data:
    data = response.data[0].get("synthesis_data", {})
    print(json.dumps(data, indent=2))
else:
    print("Not found")
