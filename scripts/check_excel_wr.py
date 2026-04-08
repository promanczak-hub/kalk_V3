import pandas as pd

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
df = pd.read_excel(excel_path, sheet_name="TAB.WR KLASA")
print(df.iloc[:, 0].dropna().tolist())
