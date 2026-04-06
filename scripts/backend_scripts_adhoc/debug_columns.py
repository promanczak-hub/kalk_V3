import pandas as pd

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
xl = pd.ExcelFile(excel_path)
df_samar = xl.parse("SAMAR")
print("Columns in SAMAR sheet:", df_samar.columns.tolist())
print(df_samar.head())
