import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def check_view():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    try:
        # Check raw table items
        res_raw = (
            supabase.table("vehicle_synthesis")
            .select("id, verification_status")
            .execute()
        )
        print(f"Total RAW rows in vehicle_synthesis: {len(res_raw.data)}")

        # Check view items
        res_view = supabase.table("fleet_management_view").select("id").execute()
        print(f"Total rows in fleet_management_view: {len(res_view.data)}")
    except Exception as e:
        print(f"Error querying view: {e}")


if __name__ == "__main__":
    check_view()
