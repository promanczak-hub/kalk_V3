import pandas as pd

df = pd.read_excel("D:\\v1_vs_v3_comparison.xlsx")
for idx, row in df.iterrows():
    v1_name = row.get("Kalkulator V1 (C# SAMAR) - Pliki i Zależności")
    v3_name = row.get("Kalkulator V3 (Python) - Opis")
    print(f"[{idx}] V1: {v1_name} | V3: {v3_name}")
