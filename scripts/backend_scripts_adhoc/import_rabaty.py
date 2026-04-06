import pandas as pd
from core.database import supabase
import sys


def import_data():
    file_path = (
        r"C:\Users\proma\Downloads\Skoda_Volkswagen_Audi_Cupra_2026_01_12 (1).xlsx"
    )
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        sys.exit(1)

    # Map the columns
    rename_map = {
        "Kalkulacja": "kalkulacja",
        "LP": "lp",
        "MODEL": "model",
        "WYPOSAŻENIE": "wyposazenie",
        "ILOŚĆ": "ilosc",
        "Numer oferty": "numer_oferty",
        "nr kalkulacji": "nr_kalkulacji",
        "uwagi": "uwagi",
        "Kontrakt": "kontrakt",
    }
    df = df.rename(columns=rename_map)

    # Handle NaN values
    records = df.to_dict("records")
    clean_records = []
    for rec in records:
        clean_rec = {}
        for k, v in rec.items():
            if pd.isna(v) or v == "brak" or v == "Brak":
                clean_rec[k] = None
            else:
                # Convert numpy types to native python types for JSON serialization
                if hasattr(v, "item"):
                    clean_rec[k] = v.item()
                else:
                    clean_rec[k] = v
        clean_records.append(clean_rec)

    # Insert to Supabase
    print(
        f"Attempting to upload {len(clean_records)} records to Supabase 'rabaty' table..."
    )
    try:
        for i in range(0, len(clean_records), 100):
            batch = clean_records[i : i + 100]
            supabase.table("rabaty").insert(batch).execute()
            print(
                f"Inserted batch {i // 100 + 1} (records {i} to {i + len(batch) - 1})"
            )
        print("Done! Data imported successfully.")
    except Exception as e:
        print(f"Error inserting into Supabase: {e}")
        print(
            "Did you remember to create the 'rabaty' table first using create_rabaty.sql?"
        )
        sys.exit(1)


if __name__ == "__main__":
    import_data()
