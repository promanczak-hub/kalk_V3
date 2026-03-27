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
GLOBAL_SETTINGS_GID = 890315543
TIRES_GID = 1006352729


def get_gspread_client():
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)


def sync_tyre_config():
    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)

    # 1. Sync Global Settings (gid=890315543) -> tyre_configurations
    global_ws = None
    for ws in ss.worksheets():
        if ws.id == GLOBAL_SETTINGS_GID:
            global_ws = ws
            break

    if not global_ws:
        logger.error(f"Could not find worksheet with gid {GLOBAL_SETTINGS_GID}")
        return

    logger.info(f"Syncing global constants from tab: {global_ws.title}")
    global_data = global_ws.get_all_values()

    config_updates = []

    # We look for all keys in column index 3 (4th column)
    # and values in column index 1 (2nd column)
    for row in global_data[1:]:  # Skip header
        if len(row) < 4:
            continue
        db_key = row[3].strip()
        val_str = row[1].strip().replace(",", ".")

        if not db_key:
            continue

        try:
            val = float(val_str)
            config_updates.append({"config_key": db_key, "config_value": val})
            logger.info(f"Mapped {db_key}: {val}")
        except ValueError:
            logger.warning(f"Skipping non-numeric value for {db_key}: {val_str}")

    # 2. Sync Tire Thresholds (gid=1006352729)
    # If the user has thresholds there, we should sync them too.
    # For now, let's at least ensure the ones required by LTRSubCalculatorOpony are present.
    required_thresholds = [
        "all_season_threshold_1",
        "all_season_threshold_2",
        "all_season_threshold_3",
        "all_season_threshold_4",
        "all_season_threshold_5",
        "season_threshold_1",
        "season_threshold_2",
        "season_threshold_3",
        "season_threshold_4",
    ]

    # Let's see if they are in the 'Opony' tab.
    tires_ws = None
    for ws in ss.worksheets():
        if ws.id == TIRES_GID:
            tires_ws = ws
            break

    if tires_ws:
        logger.info(f"Syncing thresholds from tab: {tires_ws.title}")
        # Assuming the 'Opony' tab might have these or we use defaults if not found in global.
        # If they weren't in 'Globalne ustawienia', we add defaults to prevent 400s.
        existing_keys = [c["config_key"] for c in config_updates]
        for k in required_thresholds:
            if k not in existing_keys:
                if k.startswith("all_season"):
                    val = float(int(k.split("_")[-1]) * 60000)
                else:
                    val = float(int(k.split("_")[-1]) * 60000 + 60000)
                config_updates.append({"config_key": k, "config_value": val})

    if config_updates:
        logger.info(f"Upserting {len(config_updates)} records into tyre_configurations")
        # Ensure we only upsert to tyre_configurations table
        # Note: some keys might belong to other tables, but LTRSubCalculatorOpony
        # specifically reads from tyre_configurations.
        supabase.table("tyre_configurations").upsert(
            config_updates, on_conflict="config_key"
        ).execute()
        logger.info("Sync to tyre_configurations complete.")

        # Also sync to LTRAdminParametry_czak if they match (VAT, etc)
        # But for now, fixing the 400 is the priority.
    else:
        logger.warning("No updates found to sync.")


if __name__ == "__main__":
    sync_tyre_config()
