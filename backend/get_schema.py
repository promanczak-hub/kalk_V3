import json

try:
    import pandas as pd

    file_path = r"C:\Users\proma\Downloads\cennikiopon.csv"

    try:
        df = pd.read_csv(
            file_path, sep=";", decimal=",", encoding="utf-8-sig", header=None
        )
    except:
        df = pd.read_csv(
            file_path, sep=";", decimal=",", encoding="cp1250", header=None
        )

    df.columns = [f"col_{i}" for i in range(len(df.columns))]

    columns_info = []
    for col, dtype in df.dtypes.items():
        dt_str = str(dtype)
        if "int" in dt_str or "float" in dt_str:
            ts_type = "number"
        elif "bool" in dt_str:
            ts_type = "boolean"
        else:
            ts_type = "string"
        columns_info.append({"name": col, "type": ts_type})

    print("SCHEMA_JSON_START")
    print(json.dumps(columns_info, indent=2))
    print("SCHEMA_JSON_END")

except Exception as e:
    print("Error:", e)
