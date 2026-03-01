import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

supabase_url = os.environ.get("VITE_SUPABASE_URL")
supabase_key = os.environ.get("VITE_SUPABASE_ANON_KEY")

supabase: Client = create_client(supabase_url, supabase_key)

response = (
    supabase.table("tabela_rabaty").select("*").ilike("marka", "%audi%").execute()
)
if response.data:
    for row in response.data:
        if "Q8" in str(row.get("model", "")).upper():
            print("RABAT:", row)
else:
    print("Not found")
