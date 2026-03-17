from core.database import supabase
import json
import sys

try:
    resp = supabase.rpc("rpc_get_available_filters", {"p_segment": "Premium-Sport", "p_current_filters": {}}).execute()
    result = {"status": "SUCCESS", "data": resp.data}
except Exception as e:
    result = {
        "status": "ERROR",
        "message": getattr(e, "message", str(e)),
        "details": getattr(e, "details", None)
    }

with open("rpc_err.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
