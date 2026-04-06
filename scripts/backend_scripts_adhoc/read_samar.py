import pandas as pd

file_path = "C:\\Users\\proma\\Downloads\\2503_wynik_JŁ.xlsx"
try:
    xls = pd.ExcelFile(file_path)
    print("Sheets:", xls.sheet_names)
    df_samar = pd.read_excel(file_path, sheet_name="SAMAR", nrows=50)

    with open("samar_out.txt", "w", encoding="utf-8") as f:
        f.write("=== SAMAR Sheet Headers and Rows ===\n")

        # print first few rows to see if there are tables
        for i, row in df_samar.iterrows():
            row_strings = [
                str(val).strip()
                for val in row.values
                if pd.notna(val) and str(val).strip() != ""
            ]
            if row_strings:
                f.write(f"Row {i + 1}: {' | '.join(row_strings)}\n")
except Exception as e:
    print("Error:", e)
