import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def check_all():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, created_at")
        .execute()
    )
    print("All rows in vehicle_synthesis:")
    for r in res.data:
        print(r)


if __name__ == "__main__":
    check_all()
