import pandas as pd
import sys

file_path = r'C:\Users\proma\Downloads\2503_wynik_JŁ.xlsx'

try:
    xls = pd.ExcelFile(file_path)
    print("Sheets:", xls.sheet_names)
    
    # Try to find a sheet with "Kalkulator" or "Wynik" or "Korekty"
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=50)
        print(f"\n--- Sheet: {sheet_name} ---")
        # Print first few rows or columns that might indicate corrections
        for i, row in df.iterrows():
            row_str = " | ".join([str(x) for x in row.values if pd.notna(x)])
            if "korekt" in row_str.lower() or "tabel" in row_str.lower() or len(row_str) > 20:
                print(f"Row {i}: {row_str}")

except Exception as e:
    print("Error:", e)
