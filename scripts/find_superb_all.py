import pandas as pd
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

excel_path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (3).xlsx"
sheet_name = "KALKULATOR DH (dubel)"

df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

results = {}
for i in range(len(df_raw)):
    row_str = " ".join([str(x) for x in df_raw.iloc[i].fillna("").tolist()]).lower()
    if "superb" in row_str:
        try:
            okres = str(df_raw.iloc[i, 15]).strip()
            przebieg = str(df_raw.iloc[i, 16]).strip()
            wr = str(
                df_raw.iloc[i, 56]
            ).strip()  # usually around column BC (54) or BD (55)

            row_dict = {
                "Row": i + 1,
                "Okres": okres,
                "Przebieg": przebieg,
                "Model_Name": str(df_raw.iloc[i, 5]).strip(),
                "WR_Column_54": str(df_raw.iloc[i, 54]).strip(),
                "WR_Column_55": str(df_raw.iloc[i, 55]).strip(),
                "WR_Column_56": str(df_raw.iloc[i, 56]).strip(),
                "WR_Column_57": str(df_raw.iloc[i, 57]).strip(),
            }
            results[f"Row_{i + 1}"] = row_dict
        except IndexError:
            pass

print(json.dumps(results, indent=2, ensure_ascii=False))
