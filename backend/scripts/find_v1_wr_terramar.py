import pandas as pd
import math

file_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026_final.xlsx"

try:
    print("Reading sheets...")
    xl = pd.ExcelFile(file_path)
    print("Available sheets:", xl.sheet_names)
    
    df = xl.parse("KALKULATOR DH (dubel)")
    for i, row in df.iterrows():
        row_str = " ".join([str(x) for x in row if pd.notna(x)])
        if "82856" in str(row_str) or "82 856" in str(row_str) or "140101" in str(row_str) or "172324" in str(row_str) or "GOS-26-059093" in str(row_str):
            # Print the whole row as a dictionary
            print(f"--- MATCH ROW {i} ---")
            for col, val in row.items():
                if pd.notna(val):
                    print(f"{col}: {val}")
            
    # Print the 'KOR. MARKA' sheet
    df_marka = xl.parse("KOR. MARKA")
    for i, row in df_marka.iterrows():
        row_str = " ".join([str(x) for x in row if pd.notna(x)])
        if "CUPRA" in row_str.upper() or "TERRAMAR" in row_str.upper():
            print(f"Row {i} in KOR. MARKA:", row.to_dict())
            
except Exception as e:
    print("Error:", e)
