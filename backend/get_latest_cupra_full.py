import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def get_latest_cupra():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    res = (
        supabase.table("vehicle_synthesis")
        .select("synthesis_data, created_at")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    for row in res.data:
        data = row.get("synthesis_data", {})
        dt = data.get("digital_twin", {})
        meta = dt.get("metadata", {})
        if (
            "cupra" in str(meta).lower()
            or "terramar" in str(meta).lower()
            or "cupra" in str(data.get("card_summary")).lower()
            or "terramar" in str(data.get("card_summary")).lower()
            or "cupra" in str(data.get("brand")).lower()
        ):
            with open("latest_cupra.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Dumped Cupra to latest_cupra.json")
            return
    print("Not found")


if __name__ == "__main__":
    get_latest_cupra()
