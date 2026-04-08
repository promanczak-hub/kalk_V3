import pandas as pd
import requests
import math

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
xl = pd.ExcelFile(excel_path)

# Load SAMAR mapping
df_raw = xl.parse("SAMAR", header=None)
mapping = {}
for idx, row in df_raw.iterrows():
    dh_class = str(row[1]).strip()
    samar_class = str(row[2]).strip()
    if (
        pd.notna(dh_class)
        and pd.notna(samar_class)
        and dh_class not in ["nan", "Klasa wg wytycznych DH"]
    ):
        mapping[dh_class] = samar_class
print("Loaded mapping count:", len(mapping))

target_sheets = [
    "TAB. PRZEBIEG",
    "TAB. OKRES FINAL",
    "TAB.WR KLASA",
    "KOR. MARKA",
    "TAB. DOPOSAŻENIA",
    "KOLOR",
    "NADWOZIE",
    "ROCZNIK",
]

base_url = "http://localhost:8000/api/excel-drafts/"


# Function to clean objects for JSON serialization
def clean_val(val):
    if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
        return ""
    if isinstance(val, float) and math.isinf(val):
        return ""
    return val


for sheet_name in target_sheets:
    if sheet_name not in xl.sheet_names:
        continue

    df = xl.parse(sheet_name)
    if "Unnamed" in str(df.columns[0]):
        df = xl.parse(sheet_name, header=1)

    df = df.dropna(how="all").dropna(axis=1, how="all")

    if len(df.columns) > 0:
        first_col = df.columns[0]

        def map_class(val):
            str_val = str(val).strip()
            return mapping.get(str_val, str_val)

        # Apply the mapping to the first column
        df[first_col] = df[first_col].apply(map_class)

    columns_def = []
    for i, col in enumerate(df.columns):
        columns_def.append(
            {"field": f"col_{i + 1}", "headerName": str(col), "width": 150}
        )

    data_rows = []
    for row_idx, row in df.iterrows():
        row_dict = {"id": row_idx + 1}
        for i, col in enumerate(df.columns):
            row_dict[f"col_{i + 1}"] = clean_val(row[col])
        data_rows.append(row_dict)

    payload = {"columns_def": columns_def, "data_rows": data_rows}

    try:
        r = requests.put(f"{base_url}{sheet_name}", json=payload)
        if r.status_code != 200:
            print(f"Failed to sync {sheet_name}: {r.status_code} {r.text}")
        else:
            print(f"Successfully synced {sheet_name} ({len(data_rows)} rows)")
    except Exception as e:
        print(f"Exception syncing {sheet_name}: {e}")
