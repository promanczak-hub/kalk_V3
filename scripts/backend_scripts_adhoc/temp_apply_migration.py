import psycopg2
from pathlib import Path

sql = Path(r"d:\kalk_v3\supabase\migrations\20260402214700_add_alternatives_rpcs.sql").read_text(encoding="utf-8")

conn_strings = [
    "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
    "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:5432/postgres",
    "postgresql://postgres:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
    "postgresql://postgres:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:5432/postgres",
    "postgresql://postgres:Rockyramboa17%40@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"
]

for cs in conn_strings:
    try:
        print(f"Trying {cs.split('@')[1]} with user {cs.split('://')[1].split(':')[0]}...")
        conn = psycopg2.connect(cs)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql)
        print("Success!")
        break
    except Exception as e:
        print(f"Failed: {e}")
