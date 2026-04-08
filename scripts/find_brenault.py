import pandas as pd

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"

for sheet in ["TAB.WR KLASA", "KOR. MARKA", "TAB. DOPOSAŻENIA"]:
    df = pd.read_excel(excel_path, sheet_name=sheet)
    col0 = df.iloc[:, 0].astype(str).tolist()
    matches = [c for c in col0 if "BRENAULT" in c]
    if matches:
        print(f"Found {matches} in {sheet}")
