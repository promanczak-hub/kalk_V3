import pandas as pd

file_path = "excel_dump.csv"
df = pd.read_csv(file_path, low_memory=False)

with open("korekty_out.txt", "w", encoding="utf-8") as f:
    f.write("=== Szukanie nagłówków korekt w pliku ===\n")
    for i, row in df.iterrows():
        row_strings = [
            str(val).strip().lower()
            for val in row.values
            if pd.notna(val) and str(val).strip() != ""
        ]
        row_joined = " ".join(row_strings)

        if any(
            kw in row_joined for kw in ["korekta", "tabela", "opcjonalwspółczynnik"]
        ):
            f.write(f"Row {i + 2}: {row.dropna().to_dict()}\n")

        first_col = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if first_col.isupper() and len(first_col) > 3 and "KOREKTA" in first_col:
            f.write(f"HEADER? Row {i + 2}: {first_col}\n")
