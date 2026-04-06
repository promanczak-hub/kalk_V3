import pandas as pd
from core.database import supabase
import sys


def normalize_discount(val):
    if pd.isna(val):
        return None
    try:
        if isinstance(val, str):
            val = val.replace("%", "").strip()
            # Handle cases like "15 %" or "15,5"
            val = val.replace(",", ".")
        num = float(val)
        # If it's something like 15 or 24, assume it's a percentage that needs dividing by 100
        # If it's already 0.15, leave it
        if num > 1.0:
            return num / 100.0
        return num
    except Exception:
        return None


def import_data():
    file_path = (
        r"C:\Users\proma\Downloads\Skoda_Volkswagen_Audi_Cupra_2026_01_12 (1).xlsx"
    )
    try:
        xl = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        sys.exit(1)

    sheets_to_process = [
        ("rabaty_SKODA", "SKODA"),
        ("rabaty_AUDI", "AUDI"),
        ("rabaty_VWO", "VW Osobowe"),
        ("rabaty_VWSD", "VW Dostawcze"),
        ("rabaty_SEAT_CUPRA", "SEAT/CUPRA"),
    ]

    all_records = []

    for sheet_name, marka in sheets_to_process:
        if sheet_name not in xl.sheet_names:
            print(f"Warning: Sheet {sheet_name} not found.")
            continue

        df = xl.parse(sheet_name)

        # Mapping logic based on columns present in the sheet
        cols = df.columns.tolist()

        for _, row in df.iterrows():
            record = {
                "marka": marka,
                "model": None,
                "kod": None,
                "wykluczenia": None,
                "rabat": None,
            }

            # Extract Model
            if "Model" in cols:
                record["model"] = row["Model"]
            elif "Grupa modelowa " in cols:
                record["model"] = row["Grupa modelowa "]
            elif "CUPRA Grupa modelowa " in cols:
                record["model"] = row["CUPRA Grupa modelowa "]

            # Extract Kod
            if "Kod" in cols:
                record["kod"] = row["Kod"]
            elif "Grupa modelowa" in cols and cols.count("Grupa modelowa") > 0:
                # Audi, VWO, VWSD have a second column just named 'Grupa modelowa' which holds the code
                record["kod"] = row.get("Grupa modelowa")

            # Extract Wykluczenia
            if "Wykluczenia " in cols:
                record["wykluczenia"] = row["Wykluczenia "]

            # Extract Rabat
            if "Rabat procentowy (%)" in cols:
                record["rabat"] = normalize_discount(row["Rabat procentowy (%)"])
            elif "Rabat %" in cols:
                record["rabat"] = normalize_discount(row["Rabat %"])

            # Clean up NaN/Null
            for k, v in record.items():
                if pd.isna(v) or v == "Brak" or v == "brak":
                    record[k] = None
                elif hasattr(v, "item"):
                    record[k] = v.item()

            # Only add if we actually extracted a model or code
            if record["model"] or record["kod"]:
                all_records.append(record)

    print(f"Prepared {len(all_records)} total discount records.")

    # Insert to Supabase
    print("Attempting to upload records to Supabase 'tabela_rabaty' table...")
    try:
        # Clear existing data first
        supabase.table("tabela_rabaty").delete().neq("id", 0).execute()

        for i in range(0, len(all_records), 100):
            batch = all_records[i : i + 100]
            supabase.table("tabela_rabaty").insert(batch).execute()
            print(
                f"Inserted batch {i // 100 + 1} (records {i} to {i + len(batch) - 1})"
            )
        print("Done! Data imported successfully.")
    except Exception as e:
        print(f"Error inserting into Supabase: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import_data()
