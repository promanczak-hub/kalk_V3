import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"
EXCEL_PATH = r"C:\Users\proma\Downloads\MDM_v3_FINAL_PLUS_191.xlsx"


def main():
    print("Connecting to Google Sheets...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    print("Reading reference tables from local Excel...")
    df_body = pd.read_excel(EXCEL_PATH, sheet_name="ref_body_types")
    df_cat = pd.read_excel(EXCEL_PATH, sheet_name="ref_vehicle_categories")

    ref_body = [["body_type_code", "name"]] + df_body.values.tolist()
    ref_cat = [["vehicle_category_code", "name"]] + df_cat.values.tolist()

    print("Uploading body types...")
    try:
        ws_body = ss.worksheet("ref_body_types")
    except gspread.exceptions.WorksheetNotFound:
        ws_body = ss.add_worksheet("ref_body_types", rows=100, cols=10)
    ws_body.clear()
    ws_body.update(range_name="A1:B" + str(len(ref_body)), values=ref_body)

    print("Uploading vehicle categories...")
    try:
        ws_cat = ss.worksheet("ref_vehicle_categories")
    except gspread.exceptions.WorksheetNotFound:
        ws_cat = ss.add_worksheet("ref_vehicle_categories", rows=100, cols=10)
    ws_cat.clear()
    ws_cat.update(range_name="A1:B" + str(len(ref_cat)), values=ref_cat)

    print("Applying validation rules to 'cechy' sheet...")
    ws_cechy = ss.worksheet("cechy")

    # Body context is column K (0-indexed: 10)
    # kategoria_pojazdu is column J (0-indexed: 9)

    body_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=ref_body_types!$A$2:$A$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }

    cat_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=ref_vehicle_categories!$A$2:$A$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }

    requests = [
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 10,
                    "endColumnIndex": 11,
                },
                "rule": body_rule,
            }
        },
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 9,
                    "endColumnIndex": 10,
                },
                "rule": cat_rule,
            }
        },
    ]

    ss.batch_update({"requests": requests})
    print("Success: Setup complete!")


if __name__ == "__main__":
    main()
