import pandas as pd
import requests

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
xl = pd.ExcelFile(excel_path)

# 1. Load SAMAR mapping with header=1 since row 0 is the actual headers
df_samar = xl.parse("SAMAR", header=1)
mapping = {}
for _, row in df_samar.iterrows():
    if "Klasa wg wytycznych DH" in row and "SAMAR Klasa bazowa (do RV)" in row:
        dh_class = str(row["Klasa wg wytycznych DH"]).strip()
        samar_class = str(row["SAMAR Klasa bazowa (do RV)"]).strip()
        if pd.notna(dh_class) and pd.notna(samar_class) and dh_class != "nan":
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

for sheet_name in target_sheets:
    if sheet_name not in xl.sheet_names:
        continue

    # Try different headers if the first one doesn't look like data
    df = xl.parse(sheet_name)

    # If the first column is completely Unnamed, it might need header=1. Let's inspect.
    if "Unnamed" in str(df.columns[0]):
        df = xl.parse(sheet_name, header=1)

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df.fillna("")

    # Map classes in the first column
    if len(df.columns) > 0:
        first_col = df.columns[0]

        def map_class(val):
            str_val = str(val).strip()
            return mapping.get(str_val, str_val)

        df[first_col] = df[first_col].apply(map_class)
        print(f"[{sheet_name}] mapped first column: {first_col}")

    columns_def = []
    for i, col in enumerate(df.columns):
        columns_def.append(
            {"field": f"col_{i + 1}", "headerName": str(col), "width": 150}
        )

    data_rows = []
    for row_idx, row in df.iterrows():
        row_dict = {"id": row_idx + 1}
        for i, col in enumerate(df.columns):
            row_dict[f"col_{i + 1}"] = row[col]
        data_rows.append(row_dict)

    payload = {"columns_def": columns_def, "data_rows": data_rows}

    try:
        r = requests.put(f"{base_url}{sheet_name}", json=payload)
        r.raise_for_status()
        print(f"Successfully synced {sheet_name}")
    except Exception as e:
        print(f"Failed to sync {sheet_name}: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(e.response.text)
