import os
from dotenv import load_dotenv
from core.engine import get_vehicle_from_db

load_dotenv("../frontend/.env.local")

v = get_vehicle_from_db("some-default-id-if-needed")
# Actually, I'll just query pojazdy_master directly
from supabase import create_client

supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
)
r = supabase.table("pojazdy_master").select("*").limit(1).execute()
if r.data:
    print("Keys in pojazdy_master:", list(r.data[0].keys()))
else:
    print("No data in pojazdy_master")
