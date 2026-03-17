import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from core.database import supabase

def get_rpc_definition(rpc_name: str) -> str:
    # Need to query pg_proc to get the source code of the function.
    # Since Supabase rest API doesn't expose pg_proc directly unless configured, we might not be able to do it via python client cleanly if RLS blocks it.
    # But we can try querying using a custom RPC or directly if allowed, or just use the psql command line tool if available.
    pass

# We can actually just call the RPC with empty parameters to see the output structure.
try:
    resp = supabase.rpc("rpc_get_available_filters", {
        "p_brands": [],
        "p_models": [],
        "p_samar_class_ids": [],
        "p_current_filters": {}
    }).execute()
    print("KEYS:", resp.data.keys() if isinstance(resp.data, dict) else type(resp.data))
    if isinstance(resp.data, dict):
        print("facet_groups list len:", len(resp.data.get("facet_groups", [])))
        print("boolean_filters list len:", len(resp.data.get("boolean_filters", [])))
        if resp.data.get("boolean_filters"):
            print("First bool filter:", resp.data["boolean_filters"][0])
except Exception as e:
    print("Error:", e)
