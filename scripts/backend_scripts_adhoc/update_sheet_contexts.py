import os
import logging
from dotenv import load_dotenv

# Try importing gspread, if not we will let the execution fail and install it,
# but it's likely already installed due to mdm_sync.py
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SHEET_NAME = "cechy"


def _get_gspread_client() -> gspread.Client:
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)


def run_update():
    gc = _get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet(SHEET_NAME)

    data = ws.get_all_values()
    if not data:
        logger.error("Sheet is empty.")
        return

    headers = data[0]

    # 1. Add new columns if missing
    needs_update_headers = False
    if "Powertrain_Context" not in headers:
        # insert right after Body_Context
        if "Body_Context" in headers:
            idx = headers.index("Body_Context") + 1
            headers.insert(idx, "Powertrain_Context")
        else:
            headers.append("Powertrain_Context")
        needs_update_headers = True

    if "Drivetrain_Context" not in headers:
        if "Powertrain_Context" in headers:
            idx = headers.index("Powertrain_Context") + 1
            headers.insert(idx, "Drivetrain_Context")
        else:
            headers.append("Drivetrain_Context")
        needs_update_headers = True

    # Build header indices mapping
    hmap = {h: i for i, h in enumerate(headers)}

    modified_rows_count = 0
    updated_data = [headers]

    for row in data[1:]:
        # extend row to match headers length
        while len(row) < len(headers):
            row.append("")
        # if headers got shifted, we have to insert empty cells in row
        # Actually it's safer to reconstruct the row

        # reconstruct row dict to easily manipulate
        # data[0] is original headers
        orig_row_dict = dict(zip(data[0], row[: len(data[0])]))

        # apply rules
        tech_key = orig_row_dict.get("Technical_Key", "").lower()
        body = orig_row_dict.get("Body_Context", "").strip()
        powertrain = orig_row_dict.get("Powertrain_Context", "")

        old_body = body
        old_powertrain = powertrain

        # EV Rule
        if tech_key in (
            "zasięg_wltp_dla_pojazdów_elektrycznych_w_km",
            "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh",
            "elektryczny_zasięg",
            "pojemność_akumulatora",
        ):
            body = "ALL"
            powertrain = "EV"

        # Pickupy
        if "pickup" in tech_key or "paka" in tech_key:
            if "ALL" in body or body == "":
                body = "Pickup"

        # Wywrotka
        if "wywrot" in tech_key:
            if "ALL" in body or body == "":
                body = "Wywrotka"

        # Chłodnia
        if "agregat" in tech_key or "temperatury" in tech_key or "sanepid" in tech_key:
            if "ALL" in body or body == "":
                body = "Chłodnia / Izoterma"

        # Kontener / Winda
        if "winda" in tech_key or "udźwig" in tech_key:
            if "ALL" in body or body == "":
                body = "Kontener / Van"

        # Wymiary LCV
        if (
            tech_key in ("sidewall_height_mm", "cargo_length", "cargo_volume")
            or "drzwi_tyln" in tech_key
            or "drzwi_boczn" in tech_key
            or "próg_załadunkowy" in tech_key
        ):
            if "ALL" in body or body == "":
                body = "Van / Kontener / Pickup"

        # Truck / Długodystansowe
        if (
            "tachograf" in tech_key
            or "sypialna" in tech_key
            or "spoiler" in tech_key
            or "ogrzewanie_postojowe" in tech_key
        ):
            if "ALL" in body or body == "":
                body = "Truck / Van"

        orig_row_dict["Body_Context"] = body
        orig_row_dict["Powertrain_Context"] = powertrain
        if "Drivetrain_Context" not in orig_row_dict:
            orig_row_dict["Drivetrain_Context"] = ""

        if old_body != body or old_powertrain != powertrain:
            modified_rows_count += 1
            logger.info(
                f"Updated {tech_key}: Body '{old_body}' -> '{body}', Powertrain '{old_powertrain}' -> '{powertrain}'"
            )

        # Build new row
        new_row = [str(orig_row_dict.get(h, "")) for h in headers]
        updated_data.append(new_row)

    logger.info(f"Rows modified: {modified_rows_count}")

    # write to sheet
    logger.info("Writing updates back to Google Sheet...")
    # Clear and update (batch update)
    ws.clear()
    ws.update(
        range_name=f"A1:{gspread.utils.rowcol_to_a1(len(updated_data), len(headers))}",
        values=updated_data,
    )
    logger.info("Sheet updated successfully.")


if __name__ == "__main__":
    run_update()
