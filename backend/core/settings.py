import os
import logging
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.environ.get("APP_ENV", "local")

_LOCAL_URL = "http://127.0.0.1:54321"
_LOCAL_KEY = "dummy-local-key"

SUPABASE_URL = os.environ.get("SUPABASE_URL", _LOCAL_URL)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", _LOCAL_KEY)
FRONTEND_ORIGINS = os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# Simple validation logging
if APP_ENV == "local" and "supabase.co" in SUPABASE_URL:
    logging.warning("⚠️ WARNING: APP_ENV is 'local' but SUPABASE_URL points to the online 'supabase.co' database.")
elif APP_ENV in ["production", "staging"] and "127.0.0.1" in SUPABASE_URL:
    logging.error("❌ ERROR: APP_ENV is production/staging but SUPABASE_URL points to localhost!")
