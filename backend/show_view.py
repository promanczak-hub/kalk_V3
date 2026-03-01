import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

supabase_url = os.environ.get("VITE_SUPABASE_URL")
supabase_key = os.environ.get("VITE_SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("No supabase credentials found.")
    exit(1)

# We cannot easily get view definition via postgREST unless it's exposed.
# But we can query 1 row from the view to see what columns it has!
supabase: Client = create_client(supabase_url, supabase_key)

response = supabase.table("fleet_management_view").select("*").limit(1).execute()
if response.data:
    print("Columns in fleet_management_view:")
    print(list(response.data[0].keys()))
else:
    print("No data in view to infer columns or error.")
