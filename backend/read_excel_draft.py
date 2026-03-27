import pandas as pd

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
xl = pd.ExcelFile(excel_path)
print("Sheets in Excel:")
for sheet in xl.sheet_names:
    print(f"  - {sheet}")

# Let's read the 'SAMAR' sheet to see the mapping
if "SAMAR" in xl.sheet_names:
    df_samar = pd.read_excel(excel_path, sheet_name="SAMAR")
    print("\nSAMAR mapping sample:")
    print(df_samar.head(15))

# Try reading one of the tables like TAB. PRZEBIEG
for sheet in xl.sheet_names:
    if "PRZEBIEG" in sheet.upper() or "OKRES" in sheet.upper():
        print(f"\nSample from {sheet}:")
        df_sheet = pd.read_excel(excel_path, sheet_name=sheet)
        print(df_sheet.head(5))
        break
