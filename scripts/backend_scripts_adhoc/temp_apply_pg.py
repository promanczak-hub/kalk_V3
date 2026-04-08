import psycopg2
from pathlib import Path

MIGRATIONS_DIR = Path(r"D:\kalk_v3\supabase\migrations")
MIGRATION_FILE = MIGRATIONS_DIR / "20260402214700_add_alternatives_rpcs.sql"

DB_HOST = "aws-0-eu-central-1.pooler.supabase.com"
DB_NAME = "postgres"
DB_USER = "postgres.gnpsdiarmwvqhqbyetce"
DB_PASSWORD = "Rockyramboa17@"


def main():
    print("Connecting to Supabase Pooler...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=5432,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode="require",
            connect_timeout=15,
        )
        conn.autocommit = True
        print("CONNECTED ✓")

        sql = MIGRATION_FILE.read_text(encoding="utf-8")
        cur = conn.cursor()
        print("Executing migration...")
        cur.execute(sql)
        print("Success! Migration applied.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    main()
