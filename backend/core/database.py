import logging



from supabase import create_client, Client, ClientOptions
from core.settings import SUPABASE_URL, SUPABASE_KEY

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

options = ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
