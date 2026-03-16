import os
import logging
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.environ.get("APP_ENV", "local")

ONLINE_SUPABASE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co"

# Application is hard-pinned to the online Supabase project.
SUPABASE_URL = ONLINE_SUPABASE_URL
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
FRONTEND_ORIGINS = os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175"
)

if not SUPABASE_KEY:
    raise RuntimeError(
        "Missing required SUPABASE_KEY for online Supabase connection."
    )

if APP_ENV in ["production", "staging"] and "127.0.0.1" in SUPABASE_URL:
    logging.error(
        "ERROR: APP_ENV is production/staging but SUPABASE_URL points to localhost!"
    )
