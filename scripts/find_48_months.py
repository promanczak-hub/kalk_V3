import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet_name = "KALKULATOR DH (dubel)"

df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

# Let's search for "48" in column "Okres" (index 15) and "140" in "Przebieg" (index 16)
# specifically around row 1675-1685
search_start = 1670
search_end = 1690

header_row = df_raw.iloc[4].fillna('')
header_row2 = df_raw.iloc[5].fillna('')

for i in range(search_start, search_end):
    row_data = df_raw.iloc[i].fillna('')
    okres = str(row_data[15]).strip()
    przebieg = str(row_data[16]).strip()
    if okres == '48.0' or okres == '48' or okres == '48,0':
        if przebieg == '140.0' or przebieg == '140' or przebieg == '140,0':
            print(f"FOUND MATCH AT ROW {i+1} (index {i})")
            result = {}
            for col_idx in range(len(row_data)):
                val = row_data[col_idx]
                if val != '':
                    h1 = str(header_row[col_idx]).strip()
                    h2 = str(header_row2[col_idx]).strip()
                    col_name = f"{h1} {h2}".strip()
                    if not col_name:
                        col_name = f"Col_{col_idx}"
                    result[col_name] = str(val)
            print(json.dumps({f"Row_{i+1}": result}, indent=2, ensure_ascii=False))
