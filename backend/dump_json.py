import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

vid = "ab33d7b6-2310-474b-a87a-a5979e40da98"

o = supabase.table("ltr_kalkulacje").select("*").eq("id", vid).execute()
if o.data:
    record = o.data[0]
    stan = record.get("stan_json")
    if stan:
        fields = [
            "monthly_price_net",
            "price_net",
            "base_price_net",
            "wibor_pct",
            "margin_pct",
            "pricing_margin_pct",
            "discount_pct",
            "z_oponami",
            "replacement_car_enabled",
            "calc_matrix_trace",
            "discount",
            "_extraction_metadata",
            "toggles",
        ]
        for f in fields:
            print(f"{f}: {stan.get(f)}")
        if "card_summary" in stan:
            print(f"base_price: {stan['card_summary'].get('base_price')}")
            print(f"total_price: {stan['card_summary'].get('total_price')}")
    else:
        print("No stan_json")
else:
    print("Record not found")
