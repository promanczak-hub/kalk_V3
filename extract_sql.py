import subprocess
import csv
import io
import json

TABLES = [
    "TabelaSerwisowas",
    "Serwis",
    "LTRAdminUbezpieczenies",
    "LTRAdminStawkaZastepczies",
]


def run_sql(query):
    cmd = [
        "docker",
        "exec",
        "fleetmap-mssql",
        "/opt/mssql-tools18/bin/sqlcmd",
        "-S",
        "localhost",
        "-U",
        "sa",
        "-P",
        "FleetMap_Legacy_2026!",
        "-C",
        "-d",
        "fleetmap",
        "-W",
        "-h-1",
        "-s",
        ",",
        "-Q",
        f"SET NOCOUNT ON; {query}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return res.stdout.strip()


def export_table(table_name):
    print(f"Getting columns for {table_name}...")
    cols_out = run_sql(
        f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION"
    )
    if not cols_out:
        print(f"Table {table_name} not found or empty cols.")
        return []

    columns = [r.strip() for r in cols_out.split("\n") if r.strip()]

    # Remove DaneHistorii columns which are just audting timestamps and user IDs
    filtered_cols = [
        c for c in columns if not c.startswith("DaneHistorii_") and c != "RowTimestamp"
    ]
    col_select = ", ".join(filtered_cols)

    print(f"Selecting columns: {col_select}")
    data_out = run_sql(f"SELECT {col_select} FROM {table_name}")

    rows = []
    reader = csv.reader(io.StringIO(data_out))
    for row in reader:
        # Check to ensure row length matches
        if len(row) == len(filtered_cols):
            row_dict = {}
            for i, col in enumerate(filtered_cols):
                val = row[i].strip() if row[i] else None
                if val == "NULL" or val == "":
                    val = None
                row_dict[col] = val
            rows.append(row_dict)

    return rows


def main():
    db = {}
    for t in TABLES:
        print(f"\n--- Exporting {t} ---")
        db[t] = export_table(t)
        print(f"Got {len(db[t])} rows.")

    with open("service_insurance_data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print("\nDone. Saved to service_insurance_data.json.")


if __name__ == "__main__":
    main()
