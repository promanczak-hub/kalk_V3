import os
import logging
from supabase import create_client, Client

# Local Supabase
_LOCAL_URL = "http://127.0.0.1:54321"
_LOCAL_KEY = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"

SUPABASE_URL: str = _LOCAL_URL
SUPABASE_KEY: str = _LOCAL_KEY

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
