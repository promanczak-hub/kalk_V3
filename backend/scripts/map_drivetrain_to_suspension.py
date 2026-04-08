import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"


def main():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # 1. Update column M mapping to suspension_dict
    ws_cechy = ss.worksheet("cechy")

    req = {
        "setDataValidation": {
            "range": {
                "sheetId": ws_cechy.id,
                "startRowIndex": 1,
                "startColumnIndex": 12,  # Column M
                "endColumnIndex": 13,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_RANGE",
                    "values": [{"userEnteredValue": "=suspension_dict!$B$2:$B$100"}],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    }

    ss.batch_update({"requests": [req]})

    # 2. Delete ref_drivetrain since it's obsolete now
    try:
        ws_drivetrain = ss.worksheet("ref_drivetrain")
        ss.del_worksheet(ws_drivetrain)
    except gspread.exceptions.WorksheetNotFound:
        pass

    print("Success: Mapped column M to suspension_dict and cleaned up ref_drivetrain.")


if __name__ == "__main__":
    main()
