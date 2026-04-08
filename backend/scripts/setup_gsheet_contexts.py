import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"


def main():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # Make sure ref_drivetrain exists
    try:
        ws_drivetrain = ss.worksheet("ref_drivetrain")
    except gspread.exceptions.WorksheetNotFound:
        ws_drivetrain = ss.add_worksheet("ref_drivetrain", rows=10, cols=2)
        ws_drivetrain.update(
            range_name="A1:B5",
            values=[
                ["drivetrain_code", "name"],
                ["fwd", "Napęd na przód (FWD)"],
                ["rwd", "Napęd na tył (RWD)"],
                ["awd", "Napęd 4x4 (AWD/4WD)"],
                ["all", "Wszystkie"],
            ],
        )

    ws_cechy = ss.worksheet("cechy")

    # Kategoria_Pojazdu (J -> 9)
    # Body_Context (K -> 10)
    # Powertrain_Context (L -> 11) - map to REF_SILNIKI
    # Drivetrain_Context (M -> 12) - map to ref_drivetrain

    reqs = []

    # Map L to REF_SILNIKI
    reqs.append(
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
                        "values": [{"userEnteredValue": "=REF_SILNIKI!$B$2:$B"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        }
    )

    # Map M to ref_drivetrain
    reqs.append(
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
                        "values": [{"userEnteredValue": "=ref_drivetrain!$A$2:$A"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        }
    )

    ss.batch_update({"requests": reqs})
    print("Powertrain and Drivetrain mapped successfully.")


if __name__ == "__main__":
    main()
