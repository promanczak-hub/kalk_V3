import os
import traceback
from supabase import create_client
from dotenv import load_dotenv

try:
    load_dotenv()
    supabase_url = os.environ.get("VITE_SUPABASE_URL")
    supabase_key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(supabase_url, supabase_key)

    res = (
        supabase.table("vehicle_synthesis")
        .select("*")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    for row in res.data:
        print(
            row.get("brand"),
            row.get("model"),
            row.get("suggested_discount_pct"),
            row.get("suggested_discount_source"),
        )
except Exception:
    print("ERROR:")
    traceback.print_exc()
