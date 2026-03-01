import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

supabase_url = os.environ.get("VITE_SUPABASE_URL")
supabase_key = os.environ.get("VITE_SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("No supabase credentials found.")
    exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

response = (
    supabase.table("vehicle_synthesis")
    .select("brand, model, id")
    .ilike("model", "%Kamiq%")
    .execute()
)
print(json.dumps(response.data, indent=2))
