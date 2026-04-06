import pandas as pd

file_path = r"C:\Users\proma\Downloads\DRAFT KALKULATORA WARTOŚCI REZYDUALNYCH ver aktualna JŁ 02.02 (version 1).xlsx"
print("Reading file:", file_path)
try:
    xl = pd.ExcelFile(file_path)
    print("Sheets:")
    for s in xl.sheet_names:
        print(" - " + s)
except Exception as e:
    print("Error:", e)
