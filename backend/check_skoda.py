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

print("Fetching all Skoda discounts:")
response = (
    supabase.table("tabela_rabaty").select("*").ilike("marka", "%skoda%").execute()
)
print(json.dumps(response.data, indent=2))

print("\nFetching Škoda discounts:")
response = (
    supabase.table("tabela_rabaty").select("*").ilike("marka", "%škoda%").execute()
)
print(json.dumps(response.data, indent=2))
