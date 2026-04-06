import psycopg2
import sys

sql_file = (
    r"d:\kalk_v3\supabase\migrations\20260319102400_update_similar_vehicles_scoring.sql"
)
print(f"Executing {sql_file}...")

try:
    with open(sql_file, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres.gnpsdiarmwvqhqbyetce",
        password="Rockyramboa17@",
        host="aws-0-eu-central-1.pooler.supabase.com",
        port="6543",
        sslmode="require",
        options="-c lock_timeout=5000",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    print("Migration applied successfully!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
