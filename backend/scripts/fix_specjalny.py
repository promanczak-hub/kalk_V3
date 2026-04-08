import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
SA_KEY_PATH = r"D:\kalk_v3\backend\google_sa_key.json"


def main():
    gc = gspread.authorize(
        Credentials.from_service_account_file(
            SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    )
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws_cechy = ss.worksheet("cechy")

    # 1. Update existing cechy data in column J to only be "Osobowy", "Ciężarowy", "ALL"
    all_values = ws_cechy.get_all_values()
    cells_to_update = []

    for row_idx, row in enumerate(all_values):
        if row_idx == 0:
            continue
        while len(row) <= 12:
            row.append("")

        orig_cat = row[9]
        if orig_cat:
            cat_upper = orig_cat.upper().strip()
            new_cat = orig_cat
            if cat_upper in ["PASSENGER", "OSOBOWE"]:
                new_cat = "Osobowy"
            elif cat_upper in ["COMMERCIAL", "TRUCK", "DOSTAWCZY", "CIĘŻAROWE"]:
                new_cat = "Ciężarowy"
            elif cat_upper in ["SPECIAL", "SPECJALNY", "WSZYSTKIE"]:
                new_cat = "ALL"

            if new_cat != orig_cat:
                cells_to_update.append(
                    gspread.Cell(row=row_idx + 1, col=10, value=new_cat)
                )

    if cells_to_update:
        print(f"Updating {len(cells_to_update)} 'Kategoria_Pojazdu' cells in cechy...")
        ws_cechy.update_cells(cells_to_update)

    # 2. Ensure ALL is in body_types
    ws_body_types = ss.worksheet("body_types")
    names = [
        r[1].strip().upper() for r in ws_body_types.get_all_values()[1:] if len(r) > 1
    ]
    if "ALL" not in names:
        print("Adding ALL to body_types...")
        # Columns: ID, Nazwa_Nadwozia, Typ_Pojazdu, Podkategoria
        ws_body_types.append_row(["999", "ALL", "ALL", "ALL"])

    # 3. Apply validation rules
    print("Applying proper validation rules...")

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
    ]

    # Delete the obsolete reference sheets added previously
    for old_sheet in ["ref_body_types", "ref_vehicle_categories"]:
        try:
            ws_to_delete = ss.worksheet(old_sheet)
            requests.append({"deleteSheet": {"sheetId": ws_to_delete.id}})
            print(f"Adding request to delete {old_sheet}")
        except gspread.exceptions.WorksheetNotFound:
            pass

    ss.batch_update({"requests": requests})
    print("Validation applied. Obsolete sheets deleted.")


if __name__ == "__main__":
    main()
