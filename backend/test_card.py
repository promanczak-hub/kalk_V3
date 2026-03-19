import json
import traceback
from core.database import supabase
from core.pipeline_card_summary import generate_card_summary_from_twin

def test_reprocess():
    try:
        synth_id = "011fd704-5f53-4813-afd2-fc53ff9d2cdb" # Cupra Terramar
        resp = supabase.table("vehicle_synthesis").select("synthesis_data").not_.is_("synthesis_data", "null").limit(1).execute()
        data = resp.data[0]["synthesis_data"]
        
        cs_old = data.get("card_summary") or {}
        print("Original utility_features: " + json.dumps(cs_old.get("utility_features")), flush=True)
        
        print("Generating summary...", flush=True)
        new_data = generate_card_summary_from_twin(data)
        cs = new_data.get("card_summary") or {}
        print("New utility_features: " + json.dumps(cs.get("utility_features")), flush=True)
        print("New card_summary keys: " + json.dumps(list(cs.keys())), flush=True)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test_reprocess()
