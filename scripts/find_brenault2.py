import pandas as pd

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"

xl = pd.ExcelFile(excel_path)
for sheet in xl.sheet_names:
    df = pd.read_excel(excel_path, sheet_name=sheet)
    # Check all columns for BRENAULT
    for col in df.columns:
        matches = df[df[col].astype(str).str.contains("BRENAULT", na=False)]
        if not matches.empty:
            print(f"Found BRENAULT in sheet '{sheet}', column '{col}'")
            print(matches)
