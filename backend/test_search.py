from core.database import supabase
import json
import os
import time

with open("test_out.txt", "w", encoding="utf-8") as out:
    try:
        out.write("Testing GET INITIAL DATA...\n")
        start = time.time()
        res = supabase.rpc('rpc_get_scoring_initial_data').execute()
        out.write(f"Time: {time.time() - start:.2f}s, Results: {bool(res.data)}\n")
        if res.data:
            out.write(f"First Brand: {list(res.data.get('brands', []))[:3]}\n")

        out.write("\nTesting SEARCH...\n")
        start = time.time()
        payload = {
            "p_brands": ["Toyota"],
            "p_models": [],
            "p_samar_class_ids": [],
            "p_requirements": [{"feature_key": "monthly_price_net", "operator": "lte", "value": 5000, "requirement": "MUST_HAVE", "weight": 1}]
        }
        search = supabase.rpc("rpc_reverse_search", payload).execute()
        out.write(f"Time: {time.time() - start:.2f}s, Results: {len(search.data) if search.data else 0}\n")
        if search.data and len(search.data) > 0:
            out.write(f"Top result: {json.dumps(search.data[0], indent=2)}\n")
    except Exception as e:
        import traceback
        out.write("RAW ERROR: " + repr(e) + "\n")
        out.write(traceback.format_exc())

