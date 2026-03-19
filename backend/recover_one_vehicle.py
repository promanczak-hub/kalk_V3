import json
import os
import sys
from dotenv import load_dotenv

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.dirname(__file__))

# Path to .env in the same directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from core.extractor_v2 import process_single_twin
from core.feature_enrichment import enrich_vehicle_features
from supabase import create_client

def main():
    code = "CPYJZ25F"
    # Hardcoded known working values from test_auth_real.py
    url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
    key = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"
    
    print(f"Connecting to {url}...")
    sb = create_client(url, key)

    print(f"Searching for vehicle with code {code} in vehicle_synthesis...")
    # Using the client we just created
    res = sb.table("vehicle_synthesis").select("id, synthesis_data").execute()
    
    target_id = None
    target_data = None
    
    for row in res.data:
        sd = row.get("synthesis_data", {})
        if not sd: continue
        # Find the configuration code in the JSON
        if code in json.dumps(sd):
            target_id = row["id"]
            target_data = sd
            print(f"Match found! ID: {target_id}")
            break
            
    if not target_id:
        print(f"Vehicle {code} not found.")
        return

    print(f"Reprocessing {target_id}...")
    try:
        # process_single_twin returns a JSON string
        new_json_str = process_single_twin(target_data)
        new_data = json.loads(new_json_str)
        
        # We need a service role key for UPDATE usually if RLS is strict, 
        # but let's try with the verified working key first. 
        # If it fails with 401/403, we'll know for sure.
        print("Updating database...")
        sb.table("vehicle_synthesis").update({"synthesis_data": new_data}).eq("id", target_id).execute()
        print("Database updated.")
        
        # Enrich
        print("Running enrichment (this will use the modified feature_enrichment.py)...")
        enrich_result = enrich_vehicle_features(target_id, new_data)
        print(f"Enrichment finished: {json.dumps(enrich_result, indent=2)}")
        
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
