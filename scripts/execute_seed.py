import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    cur = conn.cursor()
    with open("d:\\kalk_v3\\seed_features.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    print("Success")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
