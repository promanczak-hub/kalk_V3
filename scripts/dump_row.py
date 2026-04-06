import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet_name = "KALKULATOR DH (dubel)"

df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
row_idx = 1678  # Row 1679

row_data = df_raw.iloc[row_idx].fillna('').tolist()

result = {}
for col_idx, val in enumerate(row_data):
    if str(val).strip() != '':
        result[f"Col_{col_idx}"] = str(val)

print(json.dumps(result, indent=2, ensure_ascii=False))
