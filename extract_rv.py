import subprocess
import csv
import io
import json

TABLES = [
    "LTRAdminTabelaWRKlasas",
    "LTRAdminKorektaWRMarkas",
    "LTRAdminTabelaWRDeprecjacjas",
    "LTRAdminTabelaWRDoposazenies",
    "LTRAdminTabelaWRPrzebiegs",
    "LTRAdminKorektaWRRoczniks",
    "LTRAdminKorektaWRKolors",
    "LTRAdminKorektaWRZabudowas",
    "KlasaWRs",
]


def run_sql(query):
    # -h-1 removes headers
    # -s"," sets comma as separator
    # -W removes trailing spaces
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
    # Get columns explicitly to be safe
    cols_out = run_sql(
        f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION"
    )
    if not cols_out:
        print(f"Table {table_name} not found or empty cols.")
        return []

    columns = [r.strip() for r in cols_out.split("\n") if r.strip()]
    col_select = ", ".join(columns)

    # We might need to cast to NVARCHAR or just let sqlcmd handle it
    data_out = run_sql(f"SELECT {col_select} FROM {table_name}")

    rows = []
    # parse the CSV out
    reader = csv.reader(io.StringIO(data_out))
    for row in reader:
        # Ignore random sqlcmd padding or warning rows
        if len(row) == len(columns):
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i].strip() if row[i] else None
                if val == "NULL" or val == "":
                    val = None
                row_dict[col] = val
            rows.append(row_dict)

    return rows


def main():
    db = {}
    for t in TABLES:
        print(f"Exporting {t}...")
        db[t] = export_table(t)
        print(f"  Got {len(db[t])} rows.")

    with open("samar_rv_data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print("Done. Saved to samar_rv_data.json.")


if __name__ == "__main__":
    main()
