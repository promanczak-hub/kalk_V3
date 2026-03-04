import os
import json
from supabase import create_client

url = "http://127.0.0.1:54321"
key = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"

supabase = create_client(url, key)
response = (
    supabase.table("vehicle_synthesis")
    .select("id, brand, model, offer_number, synthesis_data")
    .order("created_at", desc=True)
    .limit(30)
    .execute()
)

for row in response.data:
    brand = row.get("brand", "")
    model = row.get("model", "")
    if "Audi" in str(brand) or "A6" in str(model):
        print(f"ID: {row['id']}")
        print(f"Vehicle: {brand} {model} (Offer: {row['offer_number']})")

        data = row.get("synthesis_data", {})
        dt = data.get("digital_twin", {})
        card = data.get("card_summary", {})

        if "price_calculation" in dt:
            print("  YES, it has price_calculation!")
        else:
            print("  Not found at top level of digital_twin.")

        print("-" * 40)
