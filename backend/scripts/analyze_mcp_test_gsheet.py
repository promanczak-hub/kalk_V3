import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv(".env")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def analyze():
    key_path = os.getenv("GOOGLE_SA_KEY_PATH")
    if not key_path or not os.path.exists(key_path):
        print(f"Error: Service account key not found at {key_path}")
        return

    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet_id = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"

    try:
        sh = client.open_by_key(spreadsheet_id)
        results = []

        for ws in sh.worksheets():
            ws_info = {
                "title": ws.title,
                "url": ws.url,
                "headers": [],
                "rows": 0,
                "empty_cols": [],
                "data": [],
            }
            data = ws.get_all_values()

            if data:
                headers = data[0]
                ws_info["headers"] = headers
                ws_info["rows"] = len(data) - 1

                # Check for completely empty columns or missing data logic
                df = (
                    pd.DataFrame(data[1:], columns=headers)
                    if len(headers) > 0 and len(data) > 1
                    else pd.DataFrame()
                )

                if not df.empty:
                    # check missing counts per column
                    missing = df.replace("", pd.NA).isna().sum().to_dict()
                    ws_info["missing_counts"] = missing
                    ws_info["data"] = df.to_dict(orient="records")
            results.append(ws_info)

        import json

        with open("gsheet_analysis_result.json", "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "title": r["title"],
                        "headers": r["headers"],
                        "rows": r["rows"],
                        "missing_counts": r.get("missing_counts", {}),
                    }
                    for r in results
                ],
                f,
                indent=2,
                ensure_ascii=False,
            )

        print("Analysis complete. Check gsheet_analysis_result.json")
    except Exception as e:
        print(f"Failed to process sheet: {e}")


if __name__ == "__main__":
    analyze()
