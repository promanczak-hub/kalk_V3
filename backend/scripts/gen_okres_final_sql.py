import pandas as pd


def safe_float(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip().replace(",", ".").replace("%", "")
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def main():
    url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=1208281021"
    df = pd.read_csv(url)

    # skip row 0 which has 'Rok eksploatacji'
    df = df.iloc[1:]

    # Generate SQL
    sql = "INSERT INTO public.tab_okres_final (samar_class, engine_type, year_0, year_1, year_2, year_3, year_4, year_5, year_6, year_7) VALUES\n"
    values = []

    for _, row in df.iterrows():
        samar_class = str(row.iloc[0]).strip().replace("'", "''")
        engine_type = str(row.iloc[1]).strip().replace("'", "''")
        if not samar_class or samar_class.lower() == "nan":
            continue

        y0 = safe_float(row.iloc[2])
        y1 = safe_float(row.iloc[3])
        y2 = safe_float(row.iloc[4])
        y3 = safe_float(row.iloc[5])
        y4 = safe_float(row.iloc[6])
        y5 = safe_float(row.iloc[7])
        y6 = safe_float(row.iloc[8])
        y7 = safe_float(row.iloc[9])

        values.append(
            f"('{samar_class}', '{engine_type}', {y0}, {y1}, {y2}, {y3}, {y4}, {y5}, {y6}, {y7})"
        )

    sql += (
        ",\n".join(values) + "\nON CONFLICT (samar_class, engine_type) DO UPDATE SET "
    )
    sql += "year_0 = EXCLUDED.year_0, year_1 = EXCLUDED.year_1, year_2 = EXCLUDED.year_2, year_3 = EXCLUDED.year_3, "
    sql += "year_4 = EXCLUDED.year_4, year_5 = EXCLUDED.year_5, year_6 = EXCLUDED.year_6, year_7 = EXCLUDED.year_7;"

    with open("okres_final_correct.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    print("SQL generated in okres_final_correct.sql")


if __name__ == "__main__":
    main()
