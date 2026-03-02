import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../frontend/.env.local")
supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
)

r = supabase.table("samar_service_costs").select("*").limit(1).execute()
print("DATA:", r.data)
