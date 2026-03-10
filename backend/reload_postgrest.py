import psycopg2
import os
import re

with open("d:/kalk_v3/backend/.env", "r", encoding="utf-8") as f:
    env_content = f.read()

m = re.search(r"SUPABASE_DB_PASSWORD\s*=\s*(.*)", env_content)
if not m:
    with open("d:/kalk_v3/.env", "r", encoding="utf-8") as f:
        env_content = f.read()
    m = re.search(r"SUPABASE_DB_PASSWORD\s*=\s*(.*)", env_content)

if m:
    pwd = m.group(1).strip()
    conn_str = (
        f"postgresql://postgres:{pwd}@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"
    )
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "ALTER ROLE authenticator SET pgrst.db_schemas TO 'public, graphql_public, reverse_search';"
        )
        cur.execute("NOTIFY pgrst, 'reload config';")
    print("Command executed, waiting for reload...")
else:
    print("Error: Password not found in either .env files")
