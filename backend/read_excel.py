import pandas as pd
import json

file_path = r"C:\Users\proma\Downloads\DRAFT KALKULATORA WARTOŚCI REZYDUALNYCH ver aktualna JŁ 02.02 (version 1).xlsx"

try:
    xl = pd.ExcelFile(file_path)
    sheets = xl.sheet_names
    print("Sheets found:", sheets)

    output = {}
    for sheet in sheets:
        df = xl.parse(sheet, nrows=10)  # read first 10 rows
        output[sheet] = df.to_json(orient="records")

    with open("excel_summary.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Excel summary saved to excel_summary.json")
except Exception as e:
    print(f"Error reading excel: {e}")
