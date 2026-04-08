import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"


def main():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # 1. Provide exact mapping rules for validations to point to Column A (the FKs) instead of B
    ws_cechy = ss.worksheet("cechy")
    requests = [
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
                            {"userEnteredValue": "=ref_vehicle_categories!$A$2:$A$100"}
                        ],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
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
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [{"userEnteredValue": "=ref_body_types!$A$2:$A$100"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
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
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [{"userEnteredValue": "=REF_SILNIKI!$A$2:$A$100"}],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
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
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [
                            {"userEnteredValue": "=suspension_dict!$A$2:$A$100"}
                        ],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
    ]
    ss.batch_update({"requests": requests})
    print("Updated data validation rules to map strictly to FK columns (Column A).")

    # 2. Build Name -> FK mappings from the GSheet dictionary sheets
    def build_rev_map(sheet_name):
        ws = ss.worksheet(sheet_name)
        data = ws.get_all_values()[1:]  # skip header
        return {row[1].strip(): row[0].strip() for row in data if len(row) >= 2}

    map_cat = build_rev_map("ref_vehicle_categories")
    map_body = build_rev_map("ref_body_types")
    map_pow = build_rev_map("REF_SILNIKI")
    map_drv = build_rev_map("suspension_dict")

    # 3. Read current cechy rows and translate Names back to FKs
    all_values = ws_cechy.get_all_values()
    cells_to_update = []

    def translate_to_fks(value_str, rev_map):
        if not value_str or value_str.upper() == "ALL":
            return value_str
        parts = [p.strip() for p in value_str.split(",")]
        fks = []
        for p in parts:
            if p in rev_map:
                fks.append(rev_map[p])
            else:
                # perhaps it's already an FK? Check if it's in the values of rev_map
                if p in rev_map.values():
                    fks.append(p)
                else:
                    fks.append(p)  # keep original if unknown
        return ",".join(
            fks
        )  # GSheet dropdown multi-select uses comma separated (without spaces for strict string mapping sometimes, but actually GSheet multiselect separates with ', ')
        # wait, GSheet uses ", " actually. But FKs are better comma-separated and trimmed if possible.
        # Let's use comma to match exactly what Google Sheets will write if multiple items are checked.

    for row_idx, row in enumerate(all_values):
        if row_idx == 0:
            continue
        while len(row) <= 12:
            row.append("")

        # Col 9 (J)
        orig_cat = row[9]
        new_cat = translate_to_fks(orig_cat, map_cat)
        if new_cat != orig_cat:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=10, value=new_cat))

        # Col 10 (K)
        orig_body = row[10]
        new_body = translate_to_fks(orig_body, map_body)
        if new_body != orig_body:
            cells_to_update.append(
                gspread.Cell(row=row_idx + 1, col=11, value=new_body)
            )

        # Col 11 (L)
        orig_pow = row[11]
        new_pow = translate_to_fks(orig_pow, map_pow)
        if new_pow != orig_pow:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=12, value=new_pow))

        # Col 12 (M)
        orig_drv = row[12]
        new_drv = translate_to_fks(orig_drv, map_drv)
        if new_drv != orig_drv:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=13, value=new_drv))

    if cells_to_update:
        print(f"Updating {len(cells_to_update)} cells back to FK equivalents...")
        ws_cechy.update_cells(cells_to_update)
        print("Success!")
    else:
        print("No cells needed translation back to FKs.")


if __name__ == "__main__":
    main()
