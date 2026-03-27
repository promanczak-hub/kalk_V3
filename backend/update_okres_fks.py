import json
from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    # 1. Fetch all samar_classes to create a mapping
    res_classes = supabase.table("samar_classes").select("id, name").execute()
    class_map = {}
    for row in res_classes.data:
        # e.g. "Terenowo-rekreacyjne (SUV) - E WYŻSZA"
        class_map[row["name"].upper()] = row["id"]

    # Temporary fallback map mimicking seed_depreciation_rates.CLASS_MAP
    # mapping from Excel strings to actual IDs
    legacy_map = {
        "A": 1,
        "Asport": 12,
        "B": 2,
        "Bsport": 13,
        "Bvan": 15,
        "Bsuv": 14,
        "C": 3,
        "Csport": 16,
        "Cvan": 18,
        "Csuv": 17,
        "D": 4,
        "Dsport": 19,
        "Dvan": 21,
        "Dsuv": 20,
        "E": 5,
        "Esuv": 22,
        "ESUV": 22,
        "F": 6,
        "Fsport": 23,
        "Fsuv": 24,
        "M": 25,
        "Mvan": 26,
        "R": 27,
        "P": 28,
        "T PICK-UP": 29,
    }

    # 2. Fetch all tab_okres_final rows
    res_final = (
        supabase.table("tab_okres_final")
        .select("id, samar_class, engine_type")
        .execute()
    )
    rows = res_final.data
    print(f"Found {len(rows)} rows in tab_okres_final")

    # 3. Engine map
    fuel_map = {
        "Pb": 1,
        "PB": 1,
        "ON": 2,
        "EV": 7,
        "PHEV": 6,
        "HEV": 5,
        "Benzyna": 1,
        "Diesel": 2,
        "Elektryczny": 7,
        "Hybryda": 5,
    }

    unique_classes = set()
    unique_engines = set()

    with open("unique_dump.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "classes": sorted(list(unique_classes)),
                "engines": sorted(list(unique_engines)),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    main()
