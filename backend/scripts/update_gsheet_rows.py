import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"
EXCEL_PATH = r"C:\Users\proma\Downloads\MDM_v3_FINAL_PLUS_191.xlsx"


def main():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # 1. Update data validations to properly point to NAME columns (Column B usually)
    ws_cechy = ss.worksheet("cechy")

    # We ensure these validations point to column B (where the Polish/display names are)
    # except Drivetrain which we did earlier, but we can do it again just in case
    # AND Powertrain to REF_SILNIKI!$B$2:$B
    # AND Body_Context to ref_body_types!$B$2:$B
    # AND kategoria_pojazdu to ref_vehicle_categories!$B$2:$B

    # Also the user mentioned "kolumna J nie jest mapowana do body types 0 czy mozesz to zmienic"
    # Actually wait, Kolumna J is 'kategoria_pojazdu'. Kolumna K is 'Body_Context'.

    requests = [
        # Column J (idx 9): kategoria_pojazdu -> ref_vehicle_categories (names)
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 9,
                    "endColumnIndex": 10,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [
                            {"userEnteredValue": "=ref_vehicle_categories!$B$2:$B$100"}
                        ],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
        # Column K (idx 10): Body_Context -> ref_body_types (names)
        {
            "setDataValidation": {
                "range": {
                    "sheetId": ws_cechy.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 10,
                    "endColumnIndex": 11,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [{"userEnteredValue": "=ref_body_types!$B$2:$B$100"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
        # Column L (idx 11): Powertrain_Context -> REF_SILNIKI (names)
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
                        "values": [{"userEnteredValue": "=REF_SILNIKI!$B$2:$B$100"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
        # Column M (idx 12): Drivetrain_Context -> suspension_dict (names)
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
                        "values": [
                            {"userEnteredValue": "=suspension_dict!$B$2:$B$100"}
                        ],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
    ]
    ss.batch_update({"requests": requests})
    print("Updated data validation rules to map to Name columns!")

    # 2. Get dictionaries from GSheet to map codes -> names
    dict_body = {
        row[0]: row[1] for row in ss.worksheet("ref_body_types").get_all_values()[1:]
    }
    dict_cat = {
        row[0]: row[1]
        for row in ss.worksheet("ref_vehicle_categories").get_all_values()[1:]
    }

    # 3. Read Excel file
    print("Reading Excel...")
    df_excel = pd.read_excel(EXCEL_PATH, sheet_name="Normalized_Catalog")
    # Build map from Original_Technical_Key -> contexts
    excel_map = {}
    for _, row in df_excel.iterrows():
        key = str(row["Original_Technical_Key"]).strip()
        excel_map[key] = {
            "cat": str(row["Vehicle_Category_FK"]).strip(),
            "body": str(row["Body_Type_FK"]).strip(),
            "powertrain": str(row["Powertrain_Context"]).strip(),
            "drivetrain": str(row["Drivetrain_Context"]).strip(),
        }

    # 4. Read GSheet
    all_values = ws_cechy.get_all_values()

    # 5. Prepare cell updates
    cells_to_update = []

    def translate_codes(value_str, code_dict):
        if value_str == "ALL" or value_str == "nan":
            return "ALL"
        parts = []
        for code in value_str.split(","):
            code = code.strip()
            # If code exists in dict, use name. Otherwise, keep code (might already be name)
            parts.append(code_dict.get(code, code))
        return ", ".join(parts)

    print("Matching rows...")
    for row_idx, row in enumerate(all_values):
        if row_idx == 0:
            continue  # Header

        # Make sure row has enough columns
        while len(row) <= 12:
            row.append("")

        key = row[0].strip()
        if key in excel_map:
            ex = excel_map[key]

            # Translate from codes to names
            cat_val = translate_codes(ex["cat"], dict_cat)
            body_val = translate_codes(ex["body"], dict_body)
            # Powertrain and drivetrain in excel are mostly ALL or names, we leave them as is for now
            # since they are usually accurate or empty
            pow_val = ex["powertrain"] if ex["powertrain"] != "nan" else ""
            drv_val = ex["drivetrain"] if ex["drivetrain"] != "nan" else ""

            # GSheet cell coords (row_idx+1, col_idx+1)
            # col J = 10, K = 11, L = 12, M = 13
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=10, value=cat_val))
            cells_to_update.append(
                gspread.Cell(row=row_idx + 1, col=11, value=body_val)
            )
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=12, value=pow_val))
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=13, value=drv_val))

    if cells_to_update:
        print(f"Updating {len(cells_to_update)} cells...")
        ws_cechy.update_cells(cells_to_update)
        print("Done!")
    else:
        print("No cells matched!")


if __name__ == "__main__":
    main()
