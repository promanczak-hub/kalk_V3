import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import supabase
from core.feature_enrichment import _load_feature_catalog, _llm_match_utility_features
import json

def test():
    # Only utility features match logic here without DB upsert
    features = _load_feature_catalog()
    feature_by_key = {f["feature_key"]: f["id"] for f in features}
    
    resp = supabase.table("vehicle_synthesis").select("id, synthesis_data").ilike("model", "%Crafter%").limit(2).execute()
    for row in resp.data:
        synthesis = row["synthesis_data"]
        card_summary = synthesis.get("card_summary", {})
        utility_features = card_summary.get("utility_features", [])
        valid_utility = [opt for opt in utility_features if opt.get("name") and opt.get("value")]
        
        if not valid_utility:
            continue
            
        print(f"Testing utility mapping for {row['id']}")
        utility_matches = _llm_match_utility_features(valid_utility, features)
        
        # Build batch items just to see them
        evidence_batch = []
        for match in utility_matches:
            feat_id = feature_by_key.get(match["feature_key"])
            if not feat_id:
                print(f"Missing ID for {match['feature_key']}")
                continue
                
            evidence_batch.append({
                "source_vehicle_id": row["id"],
                "feature_id": feat_id,
                "feature_key": match.get("feature_key"),
                "value_num": float(match.get("value_num", 0)) if match.get("value_num") else None,
                "unit": match.get("unit"),
            })
            
        print("Evidence generated for utility features:")
        print(json.dumps(evidence_batch, indent=2, ensure_ascii=False))

test()
