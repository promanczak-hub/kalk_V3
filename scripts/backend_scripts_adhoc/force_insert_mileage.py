import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv(".env")
from supabase import create_client, ClientOptions


def safe_float(v):
    if pd.isna(v) or not str(v).strip():
        return 0.0
    s_val = str(v).replace("%", "").replace(",", ".").strip()
    try:
        val = float(s_val)
        if abs(val) > 0.5:
            val = val / 100.0
        if val > 0.9999:
            val = 0.9999
        if val < -0.9999:
            val = -0.9999
        return val
    except:
        return 0.0


url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=2032958193&range=A1:D34"
df = pd.read_csv(url)

# Setup Supabase
sb_url = os.getenv("SUPABASE_URL")
sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(
    sb_url,
    sb_key,
    ClientOptions(postgrest_client_timeout=60, storage_client_timeout=60),
)

# 1. Fetch valid Samar Classes
classes_res = supabase.table("samar_classes").select("id, name").execute()
class_map = {c["name"].strip().lower(): c["id"] for c in classes_res.data}

# Hardcoded Fuel Types (1-9)
fuel_ids = list(range(1, 10))

inserts = []
for _, row in df.iterrows():
    c_name = str(row.iloc[0]).strip()
    if pd.isna(c_name) or not c_name:
        continue

    under = safe_float(row.iloc[1])
    over = safe_float(row.iloc[2])

    c_id = class_map.get(c_name.lower())
    if c_id:
        for f_id in fuel_ids:
            inserts.append(
                {
                    "samar_class_id": c_id,
                    "fuel_type_id": f_id,
                    "under_threshold_percent": under,
                    "over_threshold_percent": over,
                }
            )
    else:
        print(f"Skipping unknown class: {c_name}")

if inserts:
    print(f"Upserting {len(inserts)} rows into samar_class_mileage_corrections...")
    # Upsert in batches
    for i in range(0, len(inserts), 100):
        res = (
            supabase.table("samar_class_mileage_corrections")
            .upsert(inserts[i : i + 100], on_conflict="samar_class_id,fuel_type_id")
            .execute()
        )
    print("Done!")
else:
    print("No inserts found!")
