import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load dotenv from current directory
load_dotenv(".env")

from core.database import supabase

def check_ltr_offers():
    try:
        # Check ltr_offers
        res = supabase.table("ltr_offers").select("*").limit(1).execute()
        if res.data:
            print("Columns in ltr_offers:", list(res.data[0].keys()))
        else:
            # If no data, try to fetch column names via RPC or just assume it's correct if insert works
            print("No data in ltr_offers to check columns.")
            
    except Exception as e:
        print("Error checking ltr_offers schema:", str(e))

if __name__ == "__main__":
    check_ltr_offers()
