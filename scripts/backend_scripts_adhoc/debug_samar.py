import pandas as pd

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
xl = pd.ExcelFile(excel_path)

# Print first few rows of SAMAR without header to see raw data
df_raw = xl.parse("SAMAR", header=None)
print("Raw SAMAR top rows:")
print(df_raw.head())

mapping = {}
for idx, row in df_raw.iterrows():
    # Let's assume col 1 is DH class and col 2 is SAMAR class
    dh_class = str(row[1]).strip()
    samar_class = str(row[2]).strip()
    if (
        pd.notna(dh_class)
        and pd.notna(samar_class)
        and dh_class not in ["nan", "Klasa wg wytycznych DH"]
    ):
        mapping[dh_class] = samar_class

print("Loaded mapping count:", len(mapping))
print("Mapping sample:", list(mapping.items())[:5])
