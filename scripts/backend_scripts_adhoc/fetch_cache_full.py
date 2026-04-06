import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

res = (
    supabase.table("vehicle_matrix_cache")
    .select("*")
    .eq("vehicle_id", "ab33d7b6-2310-474b-a87a-a5979e40da98")
    .eq("months", 48)
    .eq("mileage", 120000)
    .execute()
)

if res.data:
    row = res.data[0]
    print(
        f"Stawka: {row.get('monthly_rate')} (Margin: {row.get('margin_pct')}%) | Capex: {row.get('capex_netto')}"
    )
    print(
        f"Tire: {row.get('tire_cost')} | Service: {row.get('service_cost')} | InsReq: {row.get('insurance_cost')}"
    )
    print("Keys:", row.keys())
    with open("d:/kalk_v3/backend/trace_db_ab33.json", "w", encoding="utf-8") as f:
        json.dump(row.get("calculation_trace"), f, indent=2, ensure_ascii=False)
else:
    print("Row not found")
