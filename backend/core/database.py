import os
import logging
from supabase import create_client, Client

# Online Supabase
_ONLINE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co"
_ONLINE_KEY = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", _ONLINE_URL)
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", _ONLINE_KEY)

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
