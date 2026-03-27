import os
import sys
from pathlib import Path

# Add backend dir to python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import pandas as pd
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

supabase_url = os.getenv("SUPABASE_URL", "").strip().strip('"')
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"')
print(f"Connecting to: {supabase_url}")
print(f"Key starts with: {supabase_key[:10]}...")
options = ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60)
if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
    sys.exit(1)
supabase: Client = create_client(supabase_url, supabase_key, options=options)


def safe_float(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip().replace(",", ".").replace("%", "")
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def main():
    url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=1208281021"
    print(f"Downloading from {url}...")
    df = pd.read_csv(url)

    # skip row 0 which has 'Rok eksploatacji'
    df = df.iloc[1:]

    records = []
    for _, row in df.iterrows():
        samar_class = str(row.iloc[0]).strip()
        engine_type = str(row.iloc[1]).strip()
        if not samar_class or samar_class.lower() == "nan":
            continue

        record = {
            "samar_class": samar_class,
            "engine_type": engine_type,
            "year_0": safe_float(row.iloc[2]),
            "year_1": safe_float(row.iloc[3]),
            "year_2": safe_float(row.iloc[4]),
            "year_3": safe_float(row.iloc[5]),
            "year_4": safe_float(row.iloc[6]),
            "year_5": safe_float(row.iloc[7]),
            "year_6": safe_float(row.iloc[8]),
            "year_7": safe_float(row.iloc[9]),
        }
        records.append(record)

    print(f"Parsed {len(records)} records. Inserting to tab_okres_final...")

    # clear existing data
    supabase.table("tab_okres_final").delete().neq(
        "id", "00000000-0000-0000-0000-000000000000"
    ).execute()

    # batch insert
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        res = supabase.table("tab_okres_final").insert(batch).execute()
        print(f"Inserted {len(batch)} records...")

    print("Done!")


if __name__ == "__main__":
    main()
