import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import supabase

def main():
    resp = supabase.schema("reverse_search").table("vehicle_feature_evidence").select("*").eq("source_vehicle_id", "9572afe0-00e8-415e-be99-23c348f32ac6").order("created_at", desc=True).limit(50).execute()
    numeric = [r for r in resp.data if r.get('value_num') is not None]
    print(f"Total evidence records: {len(resp.data)}, Numeric ones: {len(numeric)}")
    for r in numeric:
        print(f" - {r['feature_id']}: {r['value_num']} {r['unit']}")

main()
