import json
from core.database import supabase

if __name__ == "__main__":
    res = (
        supabase.table("vehicle_synthesis")
        .select("*")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    with open("latest_extraction.json", "w", encoding="utf-8") as f:
        json.dump(res.data[0] if res.data else {}, f, indent=2, ensure_ascii=False)
