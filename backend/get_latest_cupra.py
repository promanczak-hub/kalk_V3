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
        .select("brand, model, synthesis_data, created_at")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    for row in res.data:
        brand = row.get("brand") or ""
        if "cupra" in brand.lower() or "terramar" in str(row.get("model")).lower():
            print("Found Cupra:")
            data = row.get("synthesis_data", {})
            summary = data.get("card_summary", {})
            print("Brand:", brand, summary.get("brand"))
            print("Model:", row.get("model"), summary.get("model"))
            print("--- PRICING (Card Summary) ---")
            print("Total MSRP PLN:", summary.get("total_price_msrp_pln"))
            print("Discount Source:", summary.get("suggested_discount_source"))
            print("Discount Pct:", summary.get("suggested_discount_pct"))
            print("--- PRICING (Digital Twin) ---")
            pricing = data.get("digital_twin", {}).get("pricing", {})
            print(json.dumps(pricing, indent=2, ensure_ascii=False))
            print("=" * 40)
            return

    print("Cupra not found in recent rows.")
    for row in res.data:
        print("Recent brand:", row.get("brand"), "model:", row.get("model"))


if __name__ == "__main__":
    get_latest_cupra()
