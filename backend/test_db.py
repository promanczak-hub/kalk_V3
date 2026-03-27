from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import SUPABASE_URL, supabase


def main():
    print(f"SUPABASE_URL = {SUPABASE_URL}")

    # Check samar_classes for 26
    r1 = supabase.table("samar_classes").select("id, name").eq("id", 26).execute()
    print("Samar classes 26:", r1.data)

    # Check fuel_types / engines for 2 (Diesel)
    # The car is a 'Diesel (ON)'. Let's find out what fuel_type_id it is.
    r2 = (
        supabase.table("engines").select("id, name").ilike("name", "%Diesel%").execute()
    )
    print("Engines (Diesel):", r2.data)


if __name__ == "__main__":
    main()
