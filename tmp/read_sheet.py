import gspread
from google.oauth2.service_account import Credentials
import os
import json

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
    
    # Read Column B (Class Names) and Column C (Existing Models)
    data = ws.get("B1:C34")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    read_classes()
