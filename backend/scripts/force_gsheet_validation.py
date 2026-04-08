"""Wymusza poprawne walidacje dropdownów na arkuszu cechy.

Mapowanie słowników:
  J (idx 9)  → Kategoria_Pojazdu:  ref_vehicle_categories!$B$2:$B$100
  K (idx 10) → Body_Context:       ref_body_types!$B$2:$B$100
  L (idx 11) → Powertrain_Context: REF_SILNIKI!$B$2:$B$20
               (źródło: NapedTyp enum z extractor_models.py)
               (wartości: Benzyna(PB), Diesel(ON), mHEV, HEV, PHEV, BEV, FCEV, LPG, ALL)
  M (idx 12) → Drivetrain_Context: suspension_dict!$B$2:$B$20
               (źródło: NapedRodzaj enum z extractor_models.py)
               (wartości: ALL, FWD, RWD, AWD, 4x4, 4x2)
"""

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = r"D:\kalk_v3\backend\google_sa_key.json"


def main() -> None:
    gc = gspread.authorize(
        Credentials.from_service_account_file(
            SA_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    )
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws_cechy = ss.worksheet("cechy")

    cat_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=ref_vehicle_categories!$B$2:$B$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }
    body_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=ref_body_types!$B$2:$B$100"}],
        },
        "showCustomUi": True,
        "strict": False,
    }
    powertrain_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=REF_SILNIKI!$B$2:$B$20"}],
        },
        "showCustomUi": True,
        "strict": False,
    }
    drivetrain_rule = {
        "condition": {
            "type": "ONE_OF_RANGE",
            "values": [{"userEnteredValue": "=suspension_dict!$B$2:$B$20"}],
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
                    "startColumnIndex": 9,
                    "endColumnIndex": 10,
                },
                "rule": cat_rule,
            }
        },
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
                    "startColumnIndex": 11,
                    "endColumnIndex": 12,
                },
                "rule": powertrain_rule,
            }
        },
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 12,
                    "endColumnIndex": 13,
                },
                "rule": drivetrain_rule,
            }
        },
    ]

    print("Batch updating validation rules...")
    ss.batch_update({"requests": requests})
    print("Updated! All columns now point to correct reference sheets:")
    print("  J -> ref_vehicle_categories!$B$2:$B$100")
    print("  K -> ref_body_types!$B$2:$B$100")
    print("  L -> REF_SILNIKI!$B$2:$B$20  (NapedTyp enum)")
    print("  M -> suspension_dict!$B$2:$B$20  (FWD/RWD/AWD/ALL)")


if __name__ == "__main__":
    main()
