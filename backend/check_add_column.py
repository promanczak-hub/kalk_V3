import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # First, let's test if the column already exists
    response = (
        supabase.table("vehicle_synthesis")
        .select("original_synthesis_data")
        .limit(1)
        .execute()
    )
    print("Column 'original_synthesis_data' already exists or no error thrown.")
except Exception as e:
    if "Could not find the 'original_synthesis_data' column" in str(e):
        print(
            "Column 'original_synthesis_data' does not exist. Please run the following SQL snippet in the Supabase Dashboard SQL Editor:"
        )
        print("-" * 40)
        print(
            "ALTER TABLE vehicle_synthesis ADD COLUMN IF NOT EXISTS original_synthesis_data JSONB;"
        )
        print("-" * 40)
    else:
        print(f"Error checking for column: {e}")
