import pandas as pd
import json

file_path = r"C:\Users\proma\Downloads\2503_wynik_JŁ.xlsx"
df = pd.read_excel(file_path, sheet_name="TAB. OKRES FINAL", header=None)

# Ominięcie pierwszych pustych wierszy do momentu znalezienia nagłówka z klasami Samar lub latami
data = []
for index, row in df.head(30).iterrows():
    data.append([str(x) for x in row.tolist()[:12]])

with open("excel_dump.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
