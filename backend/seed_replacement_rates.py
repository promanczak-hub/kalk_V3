import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment logic
load_dotenv("../frontend/.env.local")
supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), os.getenv("VITE_SUPABASE_ANON_KEY")
)

# Mapping: samar_class_id -> (short_name, daily_rate_net)
# Based on user's screenshot "Klasa wynajmu" assignment:
#   A+  = id 1  (MINI)
#   B   = id 2  (MAŁE)
#   C   = id 3  (NIŻSZA ŚREDNIA)
#   D   = id 4  (ŚREDNIA)
#   E   = id 5  (WYŻSZA)
#   F   = id 6  (LUKSUSOWE)
#   SUV = ids 12,13,14,16,17,19,20,22,23,24 (SPORTOWO/TERENOWO-REKREACYJNE)
#   Mvan = ids 15,18 (VANY B/C)
#   D7   = id 21 (VANY D)
#   M    = id 25 (KOMBIVANY)
#   P    = id 26 (DOSTAWCZE KOMBI VAN, VAN)
#   PBF  = id 27 (MINIBUS)
#   R    = id 28 (DOSTAWCZE ŚREDNIE, CIĘŻKIE)
#   Tpick-up = id 29 (PICK-UP)
#   PCh  = id 30 (CIĘŻKIE DOSTAWCZE S.)
RATE_BY_CLASS_ID = {
    1: ("A+", 50.0),
    2: ("B", 60.0),
    3: ("C", 70.0),
    4: ("D", 100.0),
    5: ("E", 185.0),
    6: ("F", 250.0),
    12: ("SUV", 100.0),
    13: ("SUV", 100.0),
    14: ("SUV", 100.0),
    15: ("Mvan", 80.0),
    16: ("SUV", 100.0),
    17: ("SUV", 100.0),
    18: ("Mvan", 80.0),
    19: ("SUV", 100.0),
    20: ("SUV", 100.0),
    21: ("D7", 110.0),
    22: ("SUV", 100.0),
    23: ("SUV", 100.0),
    24: ("SUV", 100.0),
    25: ("M", 80.0),
    26: ("P", 110.0),
    27: ("PBF", 130.0),
    28: ("R", 120.0),
    29: ("Tpick-up", 110.0),
    30: ("PCh", 110.0),
}

AVERAGE_DAYS = 6.5


def seed():
    # 1. Fetch available classes from samar_classes
    r = supabase.table("samar_classes").select("id, name").order("id").execute()
    classes = r.data

    insert_data = []
    for cls in classes:
        class_id = cls["id"]
        class_name = cls["name"]
        mapping = RATE_BY_CLASS_ID.get(class_id)

        if mapping is not None:
            short_name, daily_rate = mapping
            insert_data.append(
                {
                    "samar_class_id": class_id,
                    "samar_class_name": short_name,
                    "average_days_per_year": AVERAGE_DAYS,
                    "daily_rate_net": daily_rate,
                }
            )
        else:
            print(f"⚠️  Brak stawki dla klasy {class_id}: {class_name}")

    # 2. Delete existing table data (safety reset)
    supabase.table("replacement_car_rates").delete().neq("samar_class_id", -1).execute()

    # 3. Create new rows
    if insert_data:
        res = supabase.table("replacement_car_rates").insert(insert_data).execute()
        print(f"✅ Successfully seeded {len(res.data)} rows into replacement_car_rates")
    else:
        print("❌ No data to seed")


if __name__ == "__main__":
    seed()
