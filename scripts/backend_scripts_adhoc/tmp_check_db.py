import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from core.database import supabase

def check_db():
    print(f"Checking Supabase connection...")
    try:
        # Check if table exists by trying a simple select
        res = supabase.table("body_types").select("id").limit(1).execute()
        print("SUCCESS: Table 'body_types' exists.")
        print(f"Data sample: {res.data}")
        
        # Check count
        res_count = supabase.table("body_types").select("id", count="exact").execute()
        print(f"Total rows in 'body_types': {res_count.count}")
        
    except Exception as e:
        print(f"ERROR: Could not fetch from 'body_types': {e}")

if __name__ == "__main__":
    check_db()
