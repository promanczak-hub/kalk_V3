import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def fix_stuck():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    supabase.table("vehicle_synthesis").update(
        {
            "verification_status": "error",
            "notes": "Zadanie przerwane przez restart serwera (hot-reload) podczas edycji kodu.",
        }
    ).eq("verification_status", "processing").execute()
    print("Zmieniono status zawieszonych plików na 'error'.")


if __name__ == "__main__":
    fix_stuck()
