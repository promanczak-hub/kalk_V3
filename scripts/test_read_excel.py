import pandas as pd
import json

df = pd.read_excel(
    r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx",
    sheet_name="KALKULATOR DH (dubel)",
)
# Get headers
headers = df.columns.tolist()
# Excel row 1679 -> if header is row 1, index 0 is row 2. So index 1677 is row 1679.
row = {str(k): str(v) for k, v in df.iloc[1677].fillna("").to_dict().items()}

# Let's save it to a pretty JSON
with open("d:\\kalk_v3\\excel_row.json", "w", encoding="utf-8") as f:
    json.dump(row, f, indent=4, ensure_ascii=False)
