import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def check():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    res = (
        supabase.table("vehicle_synthesis")
        .select("id, verification_status, created_at, notes, brand, model")
        .execute()
    )

    for row in res.data:
        if row.get("verification_status") not in ["completed", "error"]:
            print(f"Pending/Stuck processing doc: {row}")


if __name__ == "__main__":
    check()
