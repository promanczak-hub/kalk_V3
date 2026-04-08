import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = "D:/kalk_v3/backend/google_sa_key.json"


def main():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SA_KEY_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    # 1. Update data validations to properly point to NAME columns (Column B)
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
                            {"userEnteredValue": "=ref_vehicle_categories!$B$2:$B$100"}
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
                        "values": [{"userEnteredValue": "=ref_body_types!$B$2:$B$100"}],
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
                        "values": [{"userEnteredValue": "=REF_SILNIKI!$B$2:$B$100"}],
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
    print("Updated data validation rules to map strictly to NAME columns (Column B).")

    # 2. To avoid red triangles for "ALL", let's ensure "ALL" exists in Col B of those sheets
    def ensure_all_in_dict(sheet_name):
        ws = ss.worksheet(sheet_name)
        vals = ws.get_all_values()
        names = [r[1].strip().upper() for r in vals[1:] if len(r) > 1]
        if "ALL" not in names:
            print(f"Adding ALL to {sheet_name}...")
            ws.append_row(["ALL", "ALL"])

    ensure_all_in_dict("ref_vehicle_categories")
    ensure_all_in_dict("ref_body_types")
    ensure_all_in_dict("REF_SILNIKI")
    ensure_all_in_dict("suspension_dict")

    # 3. Build FK -> Name mappings from the GSheet dictionary sheets
    def build_fwd_map(sheet_name):
        ws = ss.worksheet(sheet_name)
        data = ws.get_all_values()[1:]  # skip header
        return {row[0].strip(): row[1].strip() for row in data if len(row) >= 2}

    map_cat = build_fwd_map("ref_vehicle_categories")
    map_body = build_fwd_map("ref_body_types")
    map_pow = build_fwd_map("REF_SILNIKI")
    map_drv = build_fwd_map("suspension_dict")

    # 4. Read current cechy rows and translate FKs back to Names
    all_values = ws_cechy.get_all_values()
    cells_to_update = []

    def translate_to_names(value_str, fwd_map):
        if not value_str or value_str.upper() == "ALL":
            return value_str
        parts = [p.strip() for p in value_str.split(",")]
        names = []
        for p in parts:
            if p in fwd_map:
                names.append(fwd_map[p])
            else:
                names.append(p)  # keep original if unknown (might already be name)
        return ", ".join(names)

    for row_idx, row in enumerate(all_values):
        if row_idx == 0:
            continue
        while len(row) <= 12:
            row.append("")

        orig_cat = row[9]
        new_cat = translate_to_names(orig_cat, map_cat)
        if new_cat != orig_cat:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=10, value=new_cat))

        orig_body = row[10]
        new_body = translate_to_names(orig_body, map_body)
        if new_body != orig_body:
            cells_to_update.append(
                gspread.Cell(row=row_idx + 1, col=11, value=new_body)
            )

        orig_pow = row[11]
        new_pow = translate_to_names(orig_pow, map_pow)
        if new_pow != orig_pow:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=12, value=new_pow))

        orig_drv = row[12]
        new_drv = translate_to_names(orig_drv, map_drv)
        if new_drv != orig_drv:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=13, value=new_drv))

    if cells_to_update:
        print(f"Updating {len(cells_to_update)} cells back to Name equivalents...")
        ws_cechy.update_cells(cells_to_update)
        print("Success!")
    else:
        print("No cells needed translation back to Names.")


if __name__ == "__main__":
    main()
