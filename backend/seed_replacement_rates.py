import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment logic
load_dotenv("../frontend/.env.local")
supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), os.getenv("VITE_SUPABASE_ANON_KEY")
)

# Mapping logic
rate_mapping = {
    1: 50.0,  # A+
    2: 60.0,  # B
    3: 70.0,  # C
    4: 100.0,  # D
    5: 185.0,  # E
    6: 250.0,  # F
    12: 100.0,  # SUV
    13: 100.0,  # SUV
    14: 100.0,  # SUV
    15: 80.0,  # Mvan
    16: 100.0,  # SUV
    17: 100.0,  # SUV
    18: 80.0,  # Mvan
    19: 100.0,  # SUV
    20: 100.0,  # SUV
    21: 80.0,  # Mvan
    22: 100.0,  # SUV
    23: 100.0,  # SUV
    24: 100.0,  # SUV
    25: 80.0,  # M
    26: 110.0,  # P
    27: 130.0,  # PBF
    28: 120.0,  # R
    29: 110.0,  # Tpick-up
    30: 120.0,  # R
}


def seed():
    # 1. Fetch available classes mapping
    r = (
        supabase.table("KlasaSAMAR_czak")
        .select("col_0, col_1")
        .order("col_0")
        .execute()
    )
    classes = r.data

    insert_data = []
    for cls in classes:
        class_id = cls["col_0"]
        class_name = cls["col_1"]
        daily_rate = rate_mapping.get(class_id)

        if daily_rate is not None:
            insert_data.append(
                {
                    "samar_class_id": class_id,
                    "samar_class_name": class_name,
                    "average_days_per_year": 6.5,
                    "daily_rate_net": daily_rate,
                }
            )

    # 2. Delete existing table data (safety reset)
    supabase.table("replacement_car_rates").delete().neq("samar_class_id", -1).execute()

    # 3. Create new rows
    res = supabase.table("replacement_car_rates").insert(insert_data).execute()
    print(f"✅ Successfully seeded {len(res.data)} rows into replacement_car_rates")


if __name__ == "__main__":
    seed()
