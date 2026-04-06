import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import supabase
import json


def main():
    resp = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, synthesis_data")
        .ilike("model", "%Crafter%")
        .order("created_at", desc=True)
        .limit(2)
        .execute()
    )
    output = []
    for row in resp.data:
        synthesis = row["synthesis_data"]
        card_summary = synthesis.get("card_summary", {})
        td = synthesis.get("technical_data", {})

        output.append(
            {
                "brand": row["brand"],
                "model": row["model"],
                "utility_features": card_summary.get("utility_features", []),
                "technical_data": td,
            }
        )
    with open("crafter_debug.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


main()
