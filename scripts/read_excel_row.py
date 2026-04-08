import pandas as pd
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet_name = "KALKULATOR DH (dubel)"

df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

target_index = 1678

if target_index < len(df_raw):
    row_data = df_raw.iloc[target_index].fillna("")
    header_row = df_raw.iloc[4].fillna("")
    header_row2 = df_raw.iloc[5].fillna("")

    result = {}
    for col_idx in range(len(row_data)):
        val = row_data[col_idx]
        if val != "":
            h1 = str(header_row[col_idx]).strip()
            h2 = str(header_row2[col_idx]).strip()
            col_name = f"{h1} {h2}".strip()
            if not col_name:
                col_name = f"Col_{col_idx}"
            result[col_name] = str(val)  # Cast to str to avoid JSON error

    print(json.dumps({"Row_1679": result}, indent=2, ensure_ascii=False))
else:
    print(f"Row 1679 not found. Max rows: {len(df_raw)}")
