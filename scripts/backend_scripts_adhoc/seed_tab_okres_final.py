import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

FILE_PATH = r"C:\Users\proma\Downloads\2503_wynik_JŁ.xlsx"

# Mapowanie BASE CODE -> SAMAR CLASS
MAPPING = {
    "A": "Podstawowa - A MINI",
    "B": "Podstawowa - B MAŁE",
    "C": "Podstawowa - C NIŻSZA ŚREDNIA",
    "D": "Podstawowa - D ŚREDNIA",
    "E": "Podstawowa - E WYŻSZA",
    "F": "Podstawowa - F LUKSUSOWE",
    "Asport": "Sportowo-rekreacyjne - A MINI",
    "Bsport": "Sportowo-rekreacyjne - B MAŁE",
    "Csport": "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA",
    "Dsport": "Sportowo-rekreacyjne - D ŚREDNIA",
    "Fsport": "Sportowo-rekreacyjne - F LUKSUSOWE",
    "Bvan": "Vany - B MICROVANY",
    "Cvan": "Vany - C MINIVANY",
    "Dvan": "Vany - D VANY",
    "Mvan": "Minibusy - I MINIBUSY",
    "Bsuv": "Terenowo-rekreacyjne (SUV) - B MAŁE",
    "Csuv": "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA",
    "Dsuv": "Terenowo-rekreacyjne (SUV) - D ŚREDNIA",
    "Esuv": "Terenowo-rekreacyjne (SUV) - E WYŻSZA",
    "Fsuv": "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE",
    "M": "Kombivany - H KOMBI-VANY",
    "R": "Sportowo-rekreacyjne - G SUPER LUKSUSOWE",
    "P": "Podstawowa - G SUPER LUKSUSOWE",
    "T PICK-UP": "Pick-up - PICK-UP",
    "CP": "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE",
}


def seed_okres_final():
    print("Reading Excel...")
    df = pd.read_excel(FILE_PATH, sheet_name="TAB. OKRES FINAL", header=None)

    samar_db = supabase.table("samar_classes").select("id, name").execute()
    samar_map = {row["name"]: row["id"] for row in samar_db.data}

    engines_db = supabase.table("engines").select("id, name").execute()
    engines_map = {row["name"]: row["id"] for row in engines_db.data}

    fuel_pb_id = engines_map.get("Benzyna (PB)", 1)
    fuel_on_id = engines_map.get("Diesel (ON)", 2)

    current_fuel_id = None
    upserts = []

    for index, row in df.iterrows():
        col0 = str(row[0]).strip()
        if col0.startswith("BENZYNA"):
            current_fuel_id = fuel_pb_id
            continue
        elif col0.startswith("DIESEL"):
            current_fuel_id = fuel_on_id
            continue

        if not current_fuel_id:
            continue

        if col0 in ["nan", "None", "", "przebiegi - np.. 35000"]:
            continue

        # Extract base code by removing 'Pb' or 'ON'
        base_code = col0
        if base_code.endswith("Pb"):
            base_code = base_code[:-2]
        elif base_code.endswith("ON"):
            base_code = base_code[:-2]

        samar_class_name = MAPPING.get(base_code)
        if not samar_class_name:
            print(f"Skipping unknown code: {col0} (base: {base_code})")
            continue

        samar_id = samar_map.get(samar_class_name)
        if not samar_id:
            print(f"SAMAR class not found in DB: {samar_class_name} for code {col0}")
            continue

        # Parse years 0-7 (Cols 1-8)
        try:
            years = [float(row[i]) for i in range(1, 9)]
        except Exception:
            # Maybe some row is not valid floats
            continue

        upserts.append(
            {
                "samar_class": samar_class_name,
                "engine_type": "Benzyna (PB)"
                if current_fuel_id == fuel_pb_id
                else "Diesel (ON)",
                "samar_class_id": samar_id,
                "fuel_type_id": current_fuel_id,
                "year_0": years[0],
                "year_1": years[1],
                "year_2": years[2],
                "year_3": years[3],
                "year_4": years[4],
                "year_5": years[5],
                "year_6": years[6],
                "year_7": years[7],
            }
        )

    print(f"Found {len(upserts)} valid records to upsert.")
    if upserts:
        try:
            res = (
                supabase.table("tab_okres_final")
                .upsert(upserts, on_conflict="samar_class,engine_type")
                .execute()
            )
            print(f"Inserted/updated {len(res.data)} records in tab_okres_final.")
        except Exception as e:
            import json

            error_data = {"exception": str(e)}
            if hasattr(e, "details"):
                error_data["details"] = e.details
            if hasattr(e, "message"):
                error_data["message"] = e.message
            if hasattr(e, "code"):
                error_data["code"] = e.code
            with open("error.json", "w") as f:
                json.dump(error_data, f, indent=2)
            print(f"Error dumped to error.json. First element: {upserts[0]}")
    else:
        print("No valid data found.")


if __name__ == "__main__":
    seed_okres_final()
