import os
import psycopg2
import re

with open("d:/kalk_v3/backend/.env", "r", encoding="utf-8") as f:
    env_content = f.read()

m = re.search(r"SUPABASE_DB_PASSWORD\s*=\s*(.*)", env_content)
if not m:
    with open("d:/kalk_v3/.env", "r", encoding="utf-8") as f:
        m = re.search(r"SUPABASE_DB_PASSWORD\s*=\s*(.*)", f.read())

if m:
    pwd = m.group(1).strip()
    conn_str = (
        f"postgresql://postgres:{pwd}@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"
    )
    conn = psycopg2.connect(conn_str)

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM reverse_search.universal_feature_categories;")
        print("Categories count:", cur.fetchone()[0])

        cur.execute("SELECT count(*) FROM reverse_search.universal_features;")
        print("Features count:", cur.fetchone()[0])

        # Test if an anonymous user can read features
        cur.execute("SET ROLE anon;")
        try:
            cur.execute("SELECT count(*) FROM reverse_search.universal_features;")
            print("Features count (anon):", cur.fetchone()[0])
        except Exception as e:
            print("Anon read failed:", str(e).strip())
else:
    print("Password not found")
