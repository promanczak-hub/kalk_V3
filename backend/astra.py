import os
import json
import sys
import traceback
from supabase import create_client
from dotenv import load_dotenv

print("Starting script...")
try:
    load_dotenv(dotenv_path="../.env")

    s_url = os.environ.get("VITE_SUPABASE_URL")
    s_key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    if not s_url:
        print("No url")
        sys.exit(1)

    s = create_client(s_url, s_key)
    res = (
        s.table("vehicle_synthesis")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    output = []
    for row in res.data:
        if "astra" in str(row.get("model", "")).lower():
            output.append(
                {
                    "brand": row.get("brand"),
                    "model": row.get("model"),
                    "pct": row.get("suggested_discount_pct"),
                    "src": row.get("suggested_discount_source"),
                }
            )

    with open("astra_discount.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("written")
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
