import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../frontend/.env.local")
supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
)

r = supabase.table("samar_classes").select("id, name").order("id").execute()
for row in r.data:
    print(f"{row['id']}: {row['name']}")
