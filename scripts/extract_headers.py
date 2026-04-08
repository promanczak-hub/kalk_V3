import pandas as pd
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet_name = "KALKULATOR DH (dubel)"
df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

headers = {}
for i in [11, 12, 14, 15, 16, 54, 55, 56, 68, 69, 73, 76]:
    h_parts = []
    for r in range(0, 6):  # top 6 rows
        val = str(df.iloc[r, i]).strip()
        if val and val != "nan":
            h_parts.append(val)
    headers[f"Col_{i}"] = " | ".join(h_parts)

print(json.dumps(headers, indent=2, ensure_ascii=False))
