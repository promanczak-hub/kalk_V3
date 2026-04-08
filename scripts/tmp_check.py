import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load dotenv from current directory
load_dotenv(".env")

from core.database import supabase


def check_schema():
    try:
        # Check vehicle_matrix_cache
        res = supabase.table("vehicle_matrix_cache").select("*").limit(1).execute()
        if res.data:
            print("Columns in vehicle_matrix_cache:", list(res.data[0].keys()))
        else:
            print("No data in vehicle_matrix_cache to check columns.")

        # Try to order by created_at to trigger the error if missing
        try:
            supabase.table("vehicle_matrix_cache").select("*").order(
                "created_at", desc=True
            ).limit(1).execute()
            print("created_at column exists.")
        except Exception as e:
            print("Error ordering by created_at (likely missing):", str(e))

    except Exception as e:
        print("Error checking schema:", str(e))


if __name__ == "__main__":
    check_schema()
