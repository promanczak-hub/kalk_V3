import sys
import os
import requests

# Set up path so we can import modules
sys.path.insert(0, os.path.abspath("."))

try:
    from core.database import supabase
    from core.settings import SUPABASE_URL

    print(f"Supabase URL: {SUPABASE_URL}")
    print("--- Testing client ---")
    resp = (
        supabase.schema("reverse_search")
        .table("model_document_sources")
        .select("id")
        .limit(1)
        .execute()
    )
    print("Supabase Table Response:", resp)
except Exception as e:
    print("Supabase Python Error:", e)

print("--- Testing DNS/HTTP connection ---")
try:
    if "SUPABASE_URL" in locals():
        res = requests.get(SUPABASE_URL, timeout=10)
        print("Raw GET request Status:", res.status_code)
except Exception as e:
    print("Network/Request Error:", e)
