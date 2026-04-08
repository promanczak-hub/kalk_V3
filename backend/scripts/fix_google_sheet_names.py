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

    def build_fwd_map(sheet_name):
        ws = ss.worksheet(sheet_name)
        data = ws.get_all_values()[1:]
        return {row[0].strip(): row[1].strip() for row in data if len(row) >= 2}

    map_cat = build_fwd_map("ref_vehicle_categories")
    map_body = build_fwd_map("ref_body_types")
    print("Map Cat:", map_cat)

    ws_cechy = ss.worksheet("cechy")
    all_values = ws_cechy.get_all_values()

    def translate_to_names(value_str, fwd_map):
        if not value_str or value_str.upper() == "ALL":
            return value_str
        parts = [p.strip() for p in value_str.split(",")]
        names = []
        for p in parts:
            if p in fwd_map:
                names.append(fwd_map[p])
            else:
                names.append(p)
        return ", ".join(names)

    cells_to_update = []
    for row_idx, row in enumerate(all_values):
        if row_idx == 0:
            continue
        while len(row) <= 12:
            row.append("")
        orig_cat = row[9]
        new_cat = translate_to_names(orig_cat, map_cat)
        if new_cat != orig_cat:
            cells_to_update.append(gspread.Cell(row=row_idx + 1, col=10, value=new_cat))
            if len(cells_to_update) <= 5:
                print(f"Row {row_idx + 1} Col 10: {orig_cat} -> {new_cat}")

        orig_body = row[10]
        new_body = translate_to_names(orig_body, map_body)
        if new_body != orig_body:
            cells_to_update.append(
                gspread.Cell(row=row_idx + 1, col=11, value=new_body)
            )

    print(f"Total cells to update: {len(cells_to_update)}")
    if cells_to_update:
        ws_cechy.update_cells(cells_to_update)
        print("Updated.")


if __name__ == "__main__":
    main()
