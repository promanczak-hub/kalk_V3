import pandas as pd

file_path = r"C:\Users\proma\Downloads\2503_wynik_JŁ.xlsx"

try:
    xls = pd.ExcelFile(file_path)
    # The first sheet seems to have a weird name, let's grab it by index
    sheet_name = xls.sheet_names[0]
    print(f"Reading sheet: {sheet_name!r}")

    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.to_csv("excel_dump.csv", index=False)
    print("Dumped to excel_dump.csv successfully.")

except Exception as e:
    print("Error:", e)
