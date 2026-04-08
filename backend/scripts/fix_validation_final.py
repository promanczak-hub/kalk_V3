"""
Fix validation rules in 'cechy' sheet:
- Col J (Kategoria_Pojazdu): Osobowy / Ciężarowy / ALL  (static list)
- Col K (Body_Context): from body_types!$B$2:$B$100  (ALL is already row ID=999)
- Col L (Powertrain_Context): from REF_SILNIKI!$B$2:$B$100 + ALL
- Col M (Drivetrain_Context): from suspension_dict!$B$2:$B$100  (ALL is row ID=1)
"""

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = r"D:\kalk_v3\backend\google_sa_key.json"


def add_all_if_missing(ws: gspread.Worksheet, id_val: str = "999") -> None:
    data = ws.get_all_values()
    names = [r[1].strip().upper() for r in data[1:] if len(r) > 1]
    if "ALL" not in names:
        ws.append_row([id_val, "ALL"])
        print(f"  → Added ALL to {ws.title}")
    else:
        idx = next(
            i
            for i, r in enumerate(data[1:], 2)
            if len(r) > 1 and r[1].strip().upper() == "ALL"
        )
        print(f"  → ALL already present in {ws.title} at row {idx}")


def main() -> None:
    gc = gspread.authorize(
        Credentials.from_service_account_file(
            SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    )
    ss = gc.open_by_key(SPREADSHEET_ID)

    # Ensure ALL exists in reference sheets
    print("Checking ALL entries...")
    add_all_if_missing(ss.worksheet("body_types"), id_val="999")
    add_all_if_missing(ss.worksheet("REF_SILNIKI"), id_val="999")
    # suspension_dict already has ALL at row 1

    ws_cechy = ss.worksheet("cechy")

    # Validation rules
    cat_rule = {
        "condition": {
            "type": "ONE_OF_LIST",
            "values": [
                {"userEnteredValue": "Osobowy"},
                {"userEnteredValue": "Ciężarowy"},
                {"userEnteredValue": "ALL"},
            ],
        },
        "showCustomUi": True,
        "strict": False,
    }

    body_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=body_types!$B$2:$B$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }

    powertrain_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=REF_SILNIKI!$B$2:$B$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }

    drivetrain_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=suspension_dict!$B$2:$B$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }

    sid = ws_cechy.id
    requests = [
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 1,
                    "startColumnIndex": 9,
                    "endColumnIndex": 10,
                },
                "rule": cat_rule,
            }
        },
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sid,
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
                    "sheetId": sid,
                    "startRowIndex": 1,
                    "startColumnIndex": 11,
                    "endColumnIndex": 12,
                },
                "rule": powertrain_rule,
            }
        },
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 1,
                    "startColumnIndex": 12,
                    "endColumnIndex": 13,
                },
                "rule": drivetrain_rule,
            }
        },
    ]

    print("Applying validation rules...")
    ss.batch_update({"requests": requests})
    print("Done! Validation rules updated:")
    print("  J (kategoria_pojazdu): Osobowy / Ciężarowy / ALL")
    print("  K (Body_Context)     : ← body_types!B")
    print("  L (Powertrain)       : ← REF_SILNIKI!B")
    print("  M (Drivetrain)       : ← suspension_dict!B  (ALL is first entry)")


if __name__ == "__main__":
    main()
