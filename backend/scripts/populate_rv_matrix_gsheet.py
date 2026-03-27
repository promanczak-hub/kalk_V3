import os
import gspread
from google.oauth2.service_account import Credentials
from core.database import supabase
from dotenv import load_dotenv

load_dotenv(".env")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def populate():
    key_path = os.getenv("GOOGLE_SA_KEY_PATH")
    spreadsheet_id = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
    sheet_gid = "1208281021"

    if not key_path or not os.path.exists(key_path):
        print(f"Error: Service account key not found at {key_path}")
        return

    # Fetch samar_classes to mapping name -> id
    classes_res = supabase.table("samar_classes").select("id, name").execute()
    class_map = {c["name"]: c["id"] for c in classes_res.data}

    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(spreadsheet_id)
    worksheet = next((ws for ws in sh.worksheets() if str(ws.id) == sheet_gid), None)

    if not worksheet:
        print(f"Error: Worksheet with GID {sheet_gid} not found.")
        return

    data = worksheet.get_all_values()
    rows_to_insert = []

    for row in data[2:]:  # Skip header
        if not row or len(row) < 10:
            continue

        name_in_sheet = row[0].strip()
        engine_type = row[1].strip()

        # Try to find matching SAMAR class ID
        class_id = class_map.get(name_in_sheet)
        if not class_id:
            # Fallback for slight naming variations
            for name, cid in class_map.items():
                if name.startswith(name_in_sheet) or name_in_sheet.startswith(name):
                    class_id = cid
                    break

        if not class_id:
            continue

        def clean_val(v):
            if not v:
                return 0.0
            try:
                # Remove % if present
                v = str(v).replace(",", ".").replace("%", "").strip()
                return float(v)
            except:
                return 0.0

        item = {
            "klasa_samar": class_id,
            "rodzaj_silnika": engine_type,
            "km_35000": clean_val(row[3]),
            "km_70000": clean_val(row[4]),
            "km_105000": clean_val(row[5]),
            "km_140000": clean_val(row[6]),
            "km_175000": clean_val(row[7]),
            "km_210000": clean_val(row[8]),
            "km_245000": clean_val(row[9]),
        }
        rows_to_insert.append(item)

    if not rows_to_insert:
        print("No data found.")
        return

    print(f"Inserting {len(rows_to_insert)} rows into tab_okres_final...")
    # Using simple insert because the table is empty and we don't have a unique constraint yet.
    # We'll rely on the (klasa_samar, rodzaj_silnika) mapping.
    batch_size = 50
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i : i + batch_size]
        try:
            supabase.table("tab_okres_final").insert(batch).execute()
            print(f"Batch {i // batch_size + 1} successful.")
        except Exception as e:
            print(f"Error in batch {i // batch_size + 1}: {e}")

    print("Populate finished.")


if __name__ == "__main__":
    populate()
