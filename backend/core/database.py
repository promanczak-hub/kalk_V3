import logging

from supabase import create_client, Client, ClientOptions
from core.settings import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

options = ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

_supabase_admin: Client | None = None


def get_fresh_client() -> Client:
    """Return a fresh Supabase client.

    Workaround for HTTP/2 'Server disconnected' errors that occur when
    the global singleton's HTTP/2 connection is terminated by Supabase
    after extended server uptime (typically after a few hours).
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=options)


def get_admin_client() -> Client:
    """Return a service_role-keyed Supabase client.

    Use for trusted server-side RPCs that exceed the anon role's
    `statement_timeout = 3s` (e.g. semantic vector batches).
    Falls back to the anon `supabase` singleton if the service-role
    key isn't configured — caller still gets a working client, but
    will hit the 3s cap.
    """
    global _supabase_admin
    if _supabase_admin is not None:
        return _supabase_admin
    if not SUPABASE_SERVICE_ROLE_KEY:
        logging.warning(
            "SUPABASE_SERVICE_ROLE_KEY not set — falling back to anon client "
            "(3s statement_timeout applies; long RPCs will be cancelled)"
        )
        return supabase
    _supabase_admin = create_client(
        SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, options=options
    )
    return _supabase_admin
