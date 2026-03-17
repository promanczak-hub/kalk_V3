import logging
import platform

# Monkeypatch platform WMI queries to prevent freezing on Windows during Supabase client initialization
_original_system = platform.system
_original_machine = platform.machine
_original_version = platform.version
_original_release = platform.release

platform.system = lambda: "Windows"
platform.machine = lambda: "AMD64"
platform.version = lambda: "10.0"
platform.release = lambda: "10"

from supabase import create_client, Client, ClientOptions
from core.settings import SUPABASE_URL, SUPABASE_KEY

logging.info(f"Using Supabase URL: {SUPABASE_URL}")

options = ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
