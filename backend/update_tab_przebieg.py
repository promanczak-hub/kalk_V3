import pandas as pd
import requests

url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=2032958193&range=A1:D34"

try:
    df = pd.read_csv(url, encoding="utf-8")

    print("Downloaded Data:")
    print(df.head())

    sheet_name = "TAB. PRZEBIEG"
    base_url = "http://localhost:8000/api/excel-drafts/"

    # Replace NaNs with empty string
    df = df.fillna("")

    columns_def = []
    for i, col in enumerate(df.columns):
        columns_def.append(
            {"field": f"col_{i + 1}", "headerName": str(col), "width": 150}
        )

    data_rows = []
    for row_idx, row in df.iterrows():
        # Using built-in int so json.dumps doesn't complain about numpy types if necessary
        row_dict = {"id": int(row_idx) + 1}
        for i, col in enumerate(df.columns):
            val = row[col]
            # convert any float that might be integers, or leave as is if string
            row_dict[f"col_{i + 1}"] = val
        data_rows.append(row_dict)

    payload = {"columns_def": columns_def, "data_rows": data_rows}

    print(f"Sending {len(data_rows)} rows to backend...")

    r = requests.put(f"{base_url}{sheet_name}", json=payload)
    r.raise_for_status()
    print(f"Successfully synced {sheet_name}")
except Exception as e:
    print(f"Script failed: {e}")
    if hasattr(e, "response") and e.response is not None:
        print(e.response.text)
