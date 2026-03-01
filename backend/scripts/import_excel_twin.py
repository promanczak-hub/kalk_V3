import sys
import math
import requests
import pandas as pd
from pathlib import Path

# The Excel file path provided by user
EXCEL_PATH = r"C:\Users\proma\Downloads\Skoda_Volkswagen_Audi_Cupra_2026_01_12 (1).xlsx"
API_URL = "http://127.0.0.1:8000/api/calculator-excel-data"


def clean_value(val):
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)) and math.isnan(val):
        return None
    # Convert pandas Timestamp to ISO string
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    return val


def import_excel():
    excel_file = Path(EXCEL_PATH)
    if not excel_file.exists():
        print(f"Error: File not found -> {EXCEL_PATH}")
        sys.exit(1)

    print(f"Loading Excel file: {EXCEL_PATH}")
    xls = pd.ExcelFile(excel_file)

    total_sheets = len(xls.sheet_names)
    print(f"Found {total_sheets} sheets: {xls.sheet_names}")

    for i, sheet_name in enumerate(xls.sheet_names, 1):
        print(f"[{i}/{total_sheets}] Processing sheet: {sheet_name}")
        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Convert dataframe to list of dicts, handling NaNs
        records = []
        for _, row in df.iterrows():
            # Convert row to dict, replace NaNs with None
            record = {str(k): clean_value(v) for k, v in row.to_dict().items()}
            records.append(record)

        payload = {"sheet_name": sheet_name, "row_data": records}

        try:
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            print(f"  ✓ Successfully imported {len(records)} rows to {sheet_name}")
        except Exception as e:
            print(f"  ✗ Error importing {sheet_name}: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"    Details: {e.response.text}")


if __name__ == "__main__":
    import_excel()
