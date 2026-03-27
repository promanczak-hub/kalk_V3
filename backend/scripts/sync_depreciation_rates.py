import os
import logging
import gspread
from google.oauth2.service_account import Credentials
from core.database import supabase
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env from backend/.env
load_dotenv()

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
DEPRECIATION_GID = 1992249665


def get_gspread_client():
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)


def normalize_name(name: str) -> str:
    return name.strip().upper().replace("KLASA ", "")


def sync_depreciation_rates():
    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)

    # Get all worksheets and find the right one by GID
    ws = next((w for w in ss.worksheets() if w.id == DEPRECIATION_GID), None)
    if not ws:
        logger.error(f"Could not find worksheet with gid {DEPRECIATION_GID}")
        return

    logger.info(f"Syncing depreciation rates from tab: {ws.title}")
    data = ws.get_all_values()
    headers = data[0]
    rows = data[1:]

    # Fetch samar_classes to map names to IDs
    resp = supabase.table("samar_classes").select("id, name").execute()
    class_map = {normalize_name(row["name"]): row["id"] for row in resp.data}

    # Map headers to DB columns
    # Spreadsheet headers: Klasa_SAMAR, Benzyna (PB), Diesel (ON), Benzyna mHEV (PB-mHEV), ...
    # DB columns: klasa_samar, benzyna_pb, diesel_on, benzyna_mhev_pb_mhev, ...
    header_to_db = {
        "Klasa_SAMAR": "klasa_samar",
        "Benzyna (PB)": "benzyna_pb",
        "Diesel (ON)": "diesel_on",
        "Benzyna mHEV (PB-mHEV)": "benzyna_mhev_pb_mhev",
        "Diesel mHEV (ON-mHEV)": "diesel_mhev_on_mhev",
        "Hybryda (HEV)": "hybryda_hev",
        "Plug-in Hybrid (PHEV)": "plug_in_hybrid_phev",
        "Elektryczny (BEV)": "elektryczny_bev",
        "Wodór (FCEV)": "wodor_fcev",
        "LPG": "lpg",
    }

    updates = []
    for row in rows:
        if not row or not row[0]:
            continue

        class_name = normalize_name(row[0])
        class_id = class_map.get(class_name)

        if class_id is None:
            logger.warning(f"Could not map SAMAR class name: {row[0]}")
            continue

        record = {"klasa_samar": class_id}
        for i, header in enumerate(headers):
            db_col = header_to_db.get(header)
            if db_col and db_col != "klasa_samar":
                try:
                    val_str = row[i].strip().replace(",", ".")
                    record[db_col] = float(val_str)
                except (ValueError, IndexError):
                    record[db_col] = 0.0

        updates.append(record)

    if updates:
        logger.info(
            f"Upserting {len(updates)} records into samar_class_depreciation_rates"
        )
        supabase.table("samar_class_depreciation_rates").upsert(
            updates, on_conflict="klasa_samar"
        ).execute()
        logger.info("Depreciation rates sync complete.")
    else:
        logger.warning("No depreciation rates found to sync.")


if __name__ == "__main__":
    sync_depreciation_rates()
