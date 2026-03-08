import pandas as pd

df = pd.read_csv(r"C:\Users\proma\Downloads\cennikopon.csv", sep=";")
classes = df["KlasaOpon"].dropna().unique()
with open("cennik_klasy.txt", "w", encoding="utf-8") as f:
    for c in classes:
        f.write(c.strip() + "\n")
