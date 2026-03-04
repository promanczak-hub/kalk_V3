import json
from core.database import supabase

try:
    res = (
        supabase.table("vehicle_synthesis")
        .select("brand", "model", "synthesis_data")
        .execute()
    )

    output = []
    for row in res.data:
        if "astra" in str(row.get("model", "")).lower():
            cs = row.get("synthesis_data", {}).get("card_summary", {})
            output.append(
                {
                    "brand": row.get("brand"),
                    "model": row.get("model"),
                    "pct": cs.get("suggested_discount_pct"),
                    "src": cs.get("suggested_discount_source"),
                }
            )

    with open("astra_discount.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Done")
except Exception as e:
    print(f"Error: {e}")
