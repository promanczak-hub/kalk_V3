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

    for sheet_name in ["ref_vehicle_categories", "ref_body_types", "cechy"]:
        ws = ss.worksheet(sheet_name)
        if sheet_name == "cechy":
            print(f"--- {sheet_name} (first 5 rows) ---")
            for row in ws.get_all_values()[:5]:
                print(row[9:11] if len(row) > 10 else row)
        else:
            print(f"--- {sheet_name} ---")
            for row in ws.get_all_values():
                print(row)


if __name__ == "__main__":
    main()
