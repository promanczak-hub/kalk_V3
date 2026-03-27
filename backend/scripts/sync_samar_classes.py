import os
import logging
import gspread
from google.oauth2.service_account import Credentials
from core.database import supabase
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
CLASSES_GID = 802400199


def get_gspread_client():
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)


def sync_samar_classes():
    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = next((w for w in ss.worksheets() if w.id == CLASSES_GID), None)

    if not ws:
        logger.error(f"Could not find worksheet with gid {CLASSES_GID}")
        return

    logger.info(f"Syncing SAMAR classes from tab: {ws.title}")
    data = ws.get_all_values()
    headers = data[0]
    rows = data[1:]

    # Map headers to DB columns
    header_to_db = {
        "ID": "id",
        "Nazwa_SAMAR": "name",
        "Example_Models": "example_models",
        "Base Period (Mo)": "base_period_months",
        "Base Mileage (km)": "base_mileage_km",
        "Mileage Threshold (km)": "mileage_threshold_km",
        "Is Metallic Enabled": "is_met_enabled",
        "Is Surcharge Enabled": "is_surcharge_enabled",
    }

    updates = []
    for row in rows:
        if not row or not row[0]:
            continue

        record = {}
        for i, header in enumerate(headers):
            db_col = header_to_db.get(header)
            if db_col:
                val = row[i].strip()
                if db_col in [
                    "id",
                    "base_period_months",
                    "base_mileage_km",
                    "mileage_threshold_km",
                ]:
                    try:
                        record[db_col] = int(val.replace(" ", ""))
                    except (ValueError, IndexError):
                        record[db_col] = 0
                elif db_col in ["is_met_enabled", "is_surcharge_enabled"]:
                    record[db_col] = val.lower() in ["true", "1", "t", "yes"]
                else:
                    record[db_col] = val

        updates.append(record)

    if updates:
        logger.info(f"Upserting {len(updates)} records into samar_classes")
        supabase.table("samar_classes").upsert(updates, on_conflict="id").execute()
        logger.info("SAMAR classes sync complete.")
    else:
        logger.warning("No SAMAR classes found to sync.")


if __name__ == "__main__":
    sync_samar_classes()
