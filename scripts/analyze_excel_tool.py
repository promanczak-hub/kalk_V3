import pandas as pd
import json
import sys

try:
    file_path = r'C:\Users\proma\Downloads\Oferta_2026-04-01_ROBELIT_PRO_SPÓŁKA_Z_OGRANICZONĄ_ODPOWIEDZIALNOŚCIĄ.xlsx'
    xl = pd.ExcelFile(file_path)
    info = {"sheets": {}}
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name)
        # Convert NaN to None for JSON
        df = df.where(pd.notnull(df), None)
        info["sheets"][sheet_name] = {
            "columns": df.columns.tolist(),
            "first_rows": df.head(10).to_dict(orient='records')
        }
    print(json.dumps(info, indent=2, ensure_ascii=False))
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)
