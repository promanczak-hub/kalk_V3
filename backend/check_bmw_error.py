import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def check_bmw():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, verification_status, notes, created_at")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    print("Ostatnie 5 dokumentów:")
    for r in res.data:
        print(
            f"ID: {r.get('id')} | Status: {r.get('verification_status')} | Marka: {r.get('brand')} | Uwagi: {r.get('notes')}"
        )


if __name__ == "__main__":
    check_bmw()
