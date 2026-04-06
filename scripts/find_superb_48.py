import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet_name = "KALKULATOR DH (dubel)"

df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

results = {}
for i in range(len(df_raw)):
    row_str = " ".join([str(x) for x in df_raw.iloc[i].fillna('').tolist()]).lower()
    if 'superb' in row_str and '48' in row_str:
        # Check column index 15 for '48'
        try:
            okres = str(df_raw.iloc[i, 15]).strip()
            if '48' in okres:
                row_dict = {f"Col_{idx}": str(val).strip() for idx, val in enumerate(df_raw.iloc[i].fillna('').tolist()) if str(val).strip() != ""}
                results[f"Row_{i+1}"] = row_dict
        except IndexError:
            pass

print(json.dumps(results, indent=2, ensure_ascii=False))
