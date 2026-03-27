import pandas as pd
import json

url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=484265370"
try:
    df = pd.read_csv(url)
    records = df.to_dict(orient="records")
    with open("temp_sheet.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
except Exception as e:
    print(f"Error fetching data: {e}")
