import logging

from supabase import create_client, Client, ClientOptions
from core.settings import SUPABASE_URL, SUPABASE_KEY

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

options = ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)


def get_fresh_client() -> Client:
    """Return a fresh Supabase client.

    Workaround for HTTP/2 'Server disconnected' errors that occur when
    the global singleton's HTTP/2 connection is terminated by Supabase
    after extended server uptime (typically after a few hours).
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
