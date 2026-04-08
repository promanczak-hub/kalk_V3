import gspread
from google.oauth2.service_account import Credentials

key_path = "D:/kalk_v3/backend/google_sa_key.json"
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(key_path, scopes=scopes)
gc = gspread.authorize(creds)
ss = gc.open_by_key("1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q")

ws = ss.worksheet("body_types")
data = ws.get("A1:D25")

print("body_types contents:")
for row in data:
    print(row)
