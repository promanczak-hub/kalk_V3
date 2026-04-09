import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(r"d:\kalk_v3\backend\.env")
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

class ClientWrapper:
    def __init__(self, c):
        self.c = c
        self.c.options.schema = "reverse_search"

def test():
    sb = create_client(url, key)
    sb.options.schema = "reverse_search"  # hack to set schema
    res = sb.table("vehicle_features_summary_view").select("*").limit(2).execute()
    print(res)

test()
