import psycopg2
import json
from datetime import date, datetime

DB_URI = "postgresql://postgres:Rockyramboa17@@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"


def date_converter(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    return None


try:
    print("Connecting to DB...")
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres.gnpsdiarmwvqhqbyetce",
        password="Rockyramboa17@",
        host="aws-0-eu-central-1.pooler.supabase.com",
        port="6543",
    )
    cur = conn.cursor()

    tables_to_backup = [
        "reverse_search.universal_features",
        "reverse_search.vehicle_feature_state",
        "reverse_search.vehicle_feature_evidence",
    ]

    for table in tables_to_backup:
        print(f"Backing up {table}...")
        cur.execute(f"SELECT * FROM {table}")
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        data = [dict(zip(colnames, row)) for row in rows]

        filename = f"d:/kalk_v3/backup_{table.replace('.', '_')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=date_converter, ensure_ascii=False)

        print(f"Saved {len(rows)} rows to {filename}")

    cur.close()
    conn.close()
    print("Backup completed successfully.")

except Exception:
    import traceback

    traceback.print_exc()
