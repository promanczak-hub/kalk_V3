import pandas as pd
from core.database import supabase
import sys


def normalize_discount(val):
    if pd.isna(val):
        return None
    try:
        if isinstance(val, str):
            val = val.replace("%", "").strip()
            val = val.replace(",", ".")
        num = float(val)
        if num > 1.0:
            return num / 100.0
        return num
    except Exception:
        return None


def import_bmw_data():
    file_path = r"C:\Users\proma\Downloads\BMW siatka rabatów (1).xlsx"
    try:
        xl = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        sys.exit(1)

    df = xl.parse(xl.sheet_names[0])

    all_records = []

    for _, row in df.iterrows():
        # Clean up NaN/Null in row
        r = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

        # Determine model string (combining Seria and Kod silnikowy if available)
        model_parts = []
        if r.get("Seria"):
            model_parts.append(str(r["Seria"]))
        if r.get("Kod silnikowy"):
            model_parts.append(str(r["Kod silnikowy"]))

        model_str = " ".join(model_parts) if model_parts else None

        wykl_parts = []
        if r.get("Min. % wyposażenia"):
            wykl_parts.append(f"Min. % wyposażenia: {r['Min. % wyposażenia']}")

        record = {
            "marka": "BMW",
            "model": model_str,
            "kod": r.get("Kod modelowy"),
            "wykluczenia": " | ".join(wykl_parts) if wykl_parts else None,
            "rabat": normalize_discount(r.get("Rabat")),
        }

        # Clean up specific string None representations
        for k, v in record.items():
            if v == "Brak" or v == "brak":
                record[k] = None

        if record["model"] or record["kod"]:
            all_records.append(record)

    print(f"Prepared {len(all_records)} BMW discount records.")

    # Insert to Supabase
    print("Attempting to upload BMW records to Supabase 'tabela_rabaty' table...")
    try:
        # Delete old BMW records if any exist to avoid duplicates on re-run
        supabase.table("tabela_rabaty").delete().eq("marka", "BMW").execute()

        for i in range(0, len(all_records), 100):
            batch = all_records[i : i + 100]
            supabase.table("tabela_rabaty").insert(batch).execute()
            print(
                f"Inserted batch {i // 100 + 1} (records {i} to {i + len(batch) - 1})"
            )
        print("Done! BMW data imported successfully.")
    except Exception as e:
        print(f"Error inserting into Supabase: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import_bmw_data()
