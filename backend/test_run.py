import asyncio
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import supabase
from core.feature_enrichment import enrich_vehicle_features

logging.basicConfig(level=logging.ERROR)

def test():
    resp = supabase.table("vehicle_synthesis").select("id, synthesis_data").ilike("model", "%Crafter%").execute()
    for row in resp.data:
        synthesis = row["synthesis_data"]
        card_summary = synthesis.get("card_summary", {})
        if len(card_summary.get("utility_features", [])) > 0:
            print(f"Running enrichment for {row['id']}...")
            res = enrich_vehicle_features(row["id"], synthesis)
            print("Result:", res)
            
            # Check DB exactly after
            resp_ev = supabase.schema("reverse_search").table("vehicle_feature_evidence").select("*").eq("source_vehicle_id", row["id"]).execute()
            print(f"Evidence rows created in DB: {len(resp_ev.data)}")
            numeric = [r for r in resp_ev.data if r.get('value_num') is not None]
            for n in numeric:
                print(f" - {n['feature_id']} | {n['value_num']} {n['unit']}")
            

test()
