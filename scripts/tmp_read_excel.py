import sys
import json
import warnings

warnings.filterwarnings("ignore")

try:
    import pandas as pd
except ImportError:
    print("pandas not found. Attempting to run without poetry.")
    sys.exit(1)

file_path = "C:\\Users\\proma\\Downloads\\_cechy użytkowe_wszystkie oddziały- do uzupełnienia (2).xlsx"

try:
    xl = pd.ExcelFile(file_path)
    df = xl.parse("uzupełnić")

    # Extract columns
    columns = list(df.columns)

    # Extract 3 sample rows
    samples = []
    for _, row in df.head(3).iterrows():
        samples.append({k: str(v) for k, v in row.items() if pd.notnull(v)})

    output = {"columns": columns, "sample_rows": samples}

    with open("d:\\kalk_v3\\excel_info.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Successfully wrote excel_info.json")
except Exception as e:
    print(f"Error reading file: {e}")
