import psycopg2
import sys

db_url = "postgresql://postgres:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        with open("../supabase/migrations/20260319110000_fix_margin_double_apply.sql", "r", encoding="utf-8") as f:
            sql = f.read()
            cur.execute(sql)
    print("Migration applied successfully!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
