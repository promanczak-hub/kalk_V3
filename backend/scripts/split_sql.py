import re


def main():
    with open("okres_final_correct.sql", "r", encoding="utf-8") as f:
        content = f.read()

    # Extract values: they are between VALUES and ON CONFLICT
    match = re.search(r"VALUES\n(.*?)\nON CONFLICT", content, re.DOTALL)
    if not match:
        print("Could not find values")
        return

    all_values = match.group(1).split(",\n")
    batch_size = 50

    header = "INSERT INTO public.tab_okres_final (samar_class, engine_type, year_0, year_1, year_2, year_3, year_4, year_5, year_6, year_7) VALUES\n"
    footer = "\nON CONFLICT (samar_class, engine_type) DO UPDATE SET year_0=EXCLUDED.year_0, year_1=EXCLUDED.year_1, year_2=EXCLUDED.year_2, year_3=EXCLUDED.year_3, year_4=EXCLUDED.year_4, year_5=EXCLUDED.year_5, year_6=EXCLUDED.year_6, year_7=EXCLUDED.year_7;"

    for i in range(0, len(all_values), batch_size):
        batch = all_values[i : i + batch_size]
        batch_sql = header + ",\n".join(batch) + footer
        with open(f"batch_{i // batch_size}.sql", "w", encoding="utf-8") as f:
            f.write(batch_sql)
        print(f"Generated batch_{i // batch_size}.sql")


if __name__ == "__main__":
    main()
