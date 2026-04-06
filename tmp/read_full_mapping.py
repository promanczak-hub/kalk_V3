import gspread
from google.oauth2.service_account import Credentials

def get_gspread_client():
    key_path = "D:/kalk_v3/backend/google_sa_key.json"
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)

def read_classes():
    SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
    CLASSES_GID = 802400199
    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = next((w for w in ss.worksheets() if w.id == CLASSES_GID), None)
    
    if not ws:
        print("Worksheet not found")
        return
    
    # Read Column B (Class Names) 1-indexed for row numbers
    classes = ws.col_values(2) # Column B
    for i, c in enumerate(classes[:35]):
        print(f"{i+1}: {c}")

if __name__ == "__main__":
    read_classes()
