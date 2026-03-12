import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import supabase

def main():
    resp = supabase.schema("reverse_search").table("vehicle_feature_evidence").select("value_num, unit, feature_id, source_type, universal_features!inner(feature_key)").order("created_at", desc=True).limit(50).execute()
    
    numeric_features = [r for r in resp.data if r.get('value_num') is not None]
    print(f"Total rows: {len(resp.data)}, Numeric: {len(numeric_features)}")
    for row in numeric_features:
        uf = row.get("universal_features", {})
        print(f"{uf.get('feature_key')}: {row.get('value_num')} {row.get('unit')} (type: {row.get('source_type')})")

main()
