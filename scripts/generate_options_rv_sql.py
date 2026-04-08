import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment
load_dotenv(r"d:\kalk_v3\backend\.env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

# Hardcoded classes from DB (same as before)
db_classes = {
    "Autobusy - AUTOBUSY": 1,
    "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE": 2,
    "Kombivany - H KOMBI-VANY": 3,
    "Lekkie dostawcze - KOMBI VAN": 4,
    "Lekkie dostawcze - VAN": 5,
    "Minibusy - I MINIBUSY": 6,
    "Pick-up - PICK-UP": 7,
    "Podstawowa - A MINI": 8,
    "Podstawowa - B MAŁE": 9,
    "Podstawowa - C NIŻSZA ŚREDNIA": 10,
    "Podstawowa - D ŚREDNIA": 11,
    "Podstawowa - E WYŻSZA": 12,
    "Podstawowa - F LUKSUSOWE": 13,
    "Podstawowa - G SUPER LUKSUSOWE": 14,
    "Sportowo-rekreacyjne - A MINI": 15,
    "Sportowo-rekreacyjne - B MAŁE": 16,
    "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA": 17,
    "Sportowo-rekreacyjne - D ŚREDNIA": 18,
    "Sportowo-rekreacyjne - E WYŻSZA": 19,
    "Sportowo-rekreacyjne - F LUKSUSOWE": 20,
    "Sportowo-rekreacyjne - G SUPER LUKSUSOWE": 21,
    "Średnie dostawcze - ŚREDNIE DOSTAWCZE": 22,
    "Terenowo-rekreacyjne (SUV) - B MAŁE": 23,
    "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA": 24,
    "Terenowo-rekreacyjne (SUV) - D ŚREDNIA": 25,
    "Terenowo-rekreacyjne (SUV) - E WYŻSZA": 26,
    "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE": 27,
    "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE": 28,
    "Vany - B MICROVANY": 29,
    "Vany - C MINIVANY": 30,
    "Vany - D VANY": 31,
    "Vany - E WYŻSZA": 32,
    "Vany - F LUKSUSOWE": 33,
}

# Fuel Type strings to IDs
fuel_type_mapping = {
    "Benzyna (PB)": 1,
    "Diesel (ON)": 2,
    "Hybryda (HEV)": 5,
    "Hybryda-Plug-in (PHEV)": 6,
    "Plug-in Hybrid (PHEV)": 6,
    "Elektryczny (BEV)": 7,
}

# 1. Read data from local JSON file
with open("d:\\kalk_v3\\options_rv_data.json", "r", encoding="utf-8") as f:
    data_rows = json.load(f)

sql_statements = [
    "-- Migration: Seed samar_class_options_rv",
    "TRUNCATE TABLE samar_class_options_rv;",
    "",
]

count = 0
for row in data_rows:
    label = row.get("col_1")  # e.g. "Podstawowa - A MINI Benzyna (PB)"
    if not label:
        continue

    # Try to find class and fuel type in label
    found_class_id = None
    found_fuel_id = None

    # Check each class name
    for class_name, class_id in db_classes.items():
        if class_name in label:
            found_class_id = class_id
            break

    # Check each fuel type
    for fuel_name, fuel_id in fuel_type_mapping.items():
        if fuel_name in label:
            found_fuel_id = fuel_id
            break

    if found_class_id is not None and found_fuel_id is not None:
        # Years 0 to 7 are in col_2 to col_9
        for year in range(8):
            col_key = f"col_{year + 2}"
            val = row.get(col_key, 0)
            if val is not None:
                sql = f"INSERT INTO samar_class_options_rv (samar_class_id, engine_type_id, year, options_rv_percent) VALUES ({found_class_id}, {found_fuel_id}, {year}, {val});"
                sql_statements.append(sql)
                count += 1

with open("update_options_rv.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(sql_statements))

print(f"Generated {count} INSERT statements in update_options_rv.sql")
