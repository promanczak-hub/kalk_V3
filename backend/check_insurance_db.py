import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../frontend/.env.local")

supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"),
    "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz",  # Service role key to bypass RLS
)

# Fetch all table names in the public schema
res = (
    supabase.table("information_schema.tables")
    .select("table_name")
    .eq("table_schema", "public")
    .execute()
)
tables = [
    t["table_name"]
    for t in res.data
    if "ubezp" in t["table_name"].lower()
    or "insur" in t["table_name"].lower()
    or "parametry" in t["table_name"].lower()
]

print("Potential Insurance/Param tables:", tables)

# If any table is found, try to fetch a row
for t in tables:
    try:
        data = supabase.table(t).select("*").limit(1).execute()
        print(f"\nSample from {t}: {data.data}")
    except Exception as e:
        print(f"Error fetching {t}: {e}")
