import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

res = supabase.table('vehicle_matrix_cache').select('laczna_stawka_netto, margin_pct, calculation_trace, tire_cost_monthly, service_cost_monthly, insurance_cost_monthly, capex_netto').eq('vehicle_id', 'ab33d7b6-2310-474b-a87a-a5979e40da98').eq('months', 48).eq('mileage', 120000).execute()

if res.data:
    row = res.data[0]
    print(f"Stawka: {row['laczna_stawka_netto']} (Margin: {row['margin_pct']}%) | Capex: {row['capex_netto']}")
    print(f"Tire: {row['tire_cost_monthly']} | Service: {row['service_cost_monthly']} | InsReq: {row['insurance_cost_monthly']}")
    with open('d:/kalk_v3/backend/trace_db_ab33.json', 'w', encoding='utf-8') as f:
        json.dump(row['calculation_trace'], f, indent=2, ensure_ascii=False)
else:
    print("Row not found")
