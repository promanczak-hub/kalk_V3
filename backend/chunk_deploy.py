import psycopg2
import os
import re

print("Starting to parse env...")
pwd = None
try:
    with open("d:/kalk_v3/backend/.env", "r", encoding="utf-8") as f:
        m = re.search(r"SUPABASE_DB_PASSWORD\s*=\s*(.*)", f.read())
        if m:
            pwd = m.group(1).strip()
except Exception:
    pass

if not pwd:
    try:
        with open("d:/kalk_v3/.env", "r", encoding="utf-8") as f:
            m = re.search(r"SUPABASE_DB_PASSWORD\s*=\s*(.*)", f.read())
            if m:
                pwd = m.group(1).strip()
    except Exception:
        pass

if not pwd:
    print("No password found")
    exit(1)

conn_str = (
    f"postgresql://postgres:{pwd}@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"
)
conn = psycopg2.connect(conn_str)

with open("d:/kalk_v3/deploy_to_cloud.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Very basic split by semicolon, ignoring those inside quotes/strings
statements = []
current = []
in_quote = False
in_double_quote = False
for char in sql:
    if char == "'":
        if not in_double_quote:
            in_quote = not in_quote
    elif char == '"':
        if not in_quote:
            in_double_quote = not in_double_quote

    current.append(char)
    if char == ";" and not in_quote and not in_double_quote:
        stmt = "".join(current).strip()
        if stmt:
            statements.append(stmt)
        current = []

if "".join(current).strip():
    statements.append("".join(current).strip())

print(f"Executing {len(statements)} statements sequentially...")

success_count = 0
with conn.cursor() as cur:
    for i, s in enumerate(statements):
        try:
            cur.execute(s)
            success_count += 1
            conn.commit()
        except Exception as e:
            print(f"Error on statement {i}: {str(e).strip()}")
            conn.rollback()

print(f"Successfully executed {success_count} / {len(statements)} statements.")
