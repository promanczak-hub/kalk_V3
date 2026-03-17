import os
import sys
import logging
from pprint import pprint

# Set up environment and paths
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", ".env.local")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

def test_caching_and_search():
    print("--- 1. FETCHING VEHICLES FOR TEST ---")
    # Grab 3 random vehicles
    res = supabase.table("vehicle_synthesis").select("id").limit(3).execute()
    vehicles = res.data or []
    if not vehicles:
        print("No vehicles found in vehicle_synthesis table.")
        return
        
    vehicle_ids = [v["id"] for v in vehicles]
    print(f"Selected vehicles: {vehicle_ids}")
    
    print("\n--- 2. RUNNING MATRIX CACHE REFRESH ---")
    try:
        refresh_matrix_cache_for_vehicles(vehicle_ids)
    except Exception as e:
        print(f"Refresh failed: {e}")
    
    print("\n--- 3. VERIFYING CACHE ENTRIES ---")
    cache_res = supabase.table("vehicle_matrix_cache").select("*").in_("vehicle_id", vehicle_ids).execute()
    print(f"Total cache entries created: {len(cache_res.data)}")
    if cache_res.data:
        print("Sample cache entry: " + str(cache_res.data[0]))
        
    print("\n--- 4. TESTING REVERSE SEARCH RPC WITH PRICE FILTER ---")
    
    search_req = {
        "p_segment": "Premium-Sport", # You can change this or ignore if any fits
        "p_requirements": [
            {
                "feature_key": "margin_pct",
                "operator": "gte",
                "value": 0,
                "requirement": "MUST_HAVE",
                "weight": 0
            },
            {
                "feature_key": "monthly_price_net",
                "operator": "lte",
                "value": 15000,
                "requirement": "MUST_HAVE",
                "weight": 1
            }
        ]
    }
    
    print(f"Calling rpc_reverse_search with payload: {search_req}")
    try:
        rpc_res = supabase.rpc("rpc_reverse_search", search_req).execute()
        
        print(f"\nSearch results count: {len(rpc_res.data)}")
        for match in rpc_res.data:
            print(f"Match: {match['brand']} {match['model']} {match['version']} - Score: {match['match_score_pct']}%")
    except Exception as e:
        print(f"RPC failed: {e}")

if __name__ == "__main__":
    test_caching_and_search()
