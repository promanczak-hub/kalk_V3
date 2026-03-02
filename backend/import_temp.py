
try:
    import pandas as pd
    from sqlalchemy import create_engine

    print("Imports successful")

    file_path = r"C:\Users\proma\Downloads\cennikiopon.csv"

    try:
        df = pd.read_csv(
            file_path, sep=";", decimal=",", encoding="utf-8-sig", header=None
        )
    except UnicodeDecodeError:
        print("UTF-8 decoding failed. Trying cp1250...")
        df = pd.read_csv(
            file_path, sep=";", decimal=",", encoding="cp1250", header=None
        )

    print(f"Read CSV successful, rows: {len(df)}")

    df.columns = [f"col_{i}" for i in range(len(df.columns))]

    engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    df.to_sql("CennikOpon_czak", engine, if_exists="replace", index=False)
    print("SQL insert successful")

except Exception as e:
    print("Error:", e)
