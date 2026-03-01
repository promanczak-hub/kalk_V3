import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def check_discounts():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    res = supabase.table("calculator_excel_data").select("sheet_name").execute()
    print("Available sheets in DB:")
    for row in res.data:
        print("-", row.get("sheet_name"))


if __name__ == "__main__":
    check_discounts()
