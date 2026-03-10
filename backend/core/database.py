import logging
from supabase import create_client, Client
from core.settings import SUPABASE_URL, SUPABASE_KEY

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
