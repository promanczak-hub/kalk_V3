import pandas as pd
import requests
import urllib.parse
import json

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
xl = pd.ExcelFile(excel_path)

# 1. Load TAB. DOPOSAŻENIA from Excel
df_dop = xl.parse("TAB. DOPOSAŻENIA")
if "Unnamed" in str(df_dop.columns[0]):
    df_dop = xl.parse("TAB. DOPOSAŻENIA", header=1)

df_dop = df_dop.dropna(how="all").dropna(axis=1, how="all")
df_dop = df_dop.fillna("")

years_cols = df_dop.columns[1:]  # Should be 0, 1, 2, 3, 4, 5, 6, 7

# 2. Fetch existing data from backend
base_url = "http://localhost:8000/api/excel-drafts/"
sheet_name = "TAB. DOPOSAŻENIA"
url = base_url + urllib.parse.quote(sheet_name)
r = requests.get(url)
db_data = r.json()

existing_rows = db_data["data_rows"]

if len(existing_rows) != len(df_dop):
    print(f"ERROR: Row count mismatch! DB: {len(existing_rows)}, Excel: {len(df_dop)}")
    exit(1)

# 3. Create new columns_def
new_columns_def = [{"field": "col_1", "width": 250, "headerName": "KLASA"}]
for i, y_col in enumerate(years_cols):
    new_columns_def.append(
        {"field": f"col_{i + 2}", "width": 100, "headerName": str(y_col)}
    )

# 4. Update data_rows by zipping them (1-to-1 match)
new_data_rows = []
for db_row, (_, excel_row) in zip(existing_rows, df_dop.iterrows()):
    klasa = str(db_row.get("col_1", "")).strip()

    # We MUST ONLY KEEP THE ORIGINAL CLASS NAME
    new_row = {"id": db_row["id"], "col_1": klasa}

    # Map the 0-7 columns
    max_year = min(8, len(years_cols))
    for i in range(max_year):
        v = excel_row[years_cols[i]]
        # Clean percentage strings if any
        if isinstance(v, str) and "%" in v:
            v = float(v.replace("%", "").replace(",", ".")) / 100.0

        if isinstance(v, (int, float)) and pd.notna(v):
            new_row[f"col_{i + 2}"] = round(float(v), 4)
        else:
            new_row[f"col_{i + 2}"] = ""

    new_data_rows.append(new_row)

# 5. Push back to backend
payload = {"columns_def": new_columns_def, "data_rows": new_data_rows}

put_r = requests.put(url, json=payload)
put_r.raise_for_status()

print("Successfully updated TAB. DOPOSAŻENIA via 1-to-1 mapping!")
print("Sample row 0:", json.dumps(new_data_rows[0], indent=2))
print("Sample row 123:", json.dumps(new_data_rows[123], indent=2))
