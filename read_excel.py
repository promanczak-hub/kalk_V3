import pandas as pd

file_path = r"C:\Users\proma\CrossDevice\Galaxy S26 Ultra\storage\Download\_cechy użytkowe_wszystkie oddziały- do uzupełnienia (2).xlsx"
try:
    df = pd.read_excel(file_path)
    columns = list(df.columns)
    print("ALL COLUMNS (FEATURES):")
    for col in columns:
        print(f"- {col}")
except Exception as e:
    print("Error:", e)
