"""Aktualizacja walidacji dropdownów dla kolumn L i M w arkuszu cechy."""

import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)
from google.oauth2.service_account import Credentials
import gspread

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"


def main() -> None:
    creds = Credentials.from_service_account_file(
        SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws_cechy = ss.worksheet("cechy")

    requests = [
        # Kolumna L (idx 11): Powertrain_Context → REF_SILNIKI!$B$2:$B$20
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 11,
                    "endColumnIndex": 12,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [{"userEnteredValue": "=REF_SILNIKI!$B$2:$B$20"}],
                    },
                    "showCustomUi": True,
                    "strict": False,  # ostrzega (czerwony trójkąt), ale nie blokuje zapisu
                },
            }
        },
        # Kolumna M (idx 12): Drivetrain_Context → suspension_dict!$B$2:$B$20
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 12,
                    "endColumnIndex": 13,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [{"userEnteredValue": "=suspension_dict!$B$2:$B$20"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
    ]

    ss.batch_update({"requests": requests})
    print("Walidacje dropdownów zaktualizowane!")
    print("  L -> REF_SILNIKI!$B$2:$B$20")
    print("  M -> suspension_dict!$B$2:$B$20")


if __name__ == "__main__":
    main()
