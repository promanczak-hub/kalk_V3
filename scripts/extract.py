import pandas as pd
import json

path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet = "KALKULATOR DH (dubel)"

df = pd.read_excel(path, sheet_name=sheet, header=None)

# Row 1679 is index 1678
row = df.iloc[1678]

# Get the first 60 columns or so to find the relevant data
header1 = df.iloc[0]
header2 = df.iloc[1]
header3 = df.iloc[2]

output = {}
for i in range(80):
    col_name = f"{header1[i]} | {header2[i]} | {header3[i]}"
    output[col_name] = row[i]

with open("row_1679.json", "w", encoding="utf-8") as f:
    json.dump(output, f, default=str, indent=2, ensure_ascii=False)
print("Done!")
