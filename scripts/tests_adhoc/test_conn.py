import psycopg2

print("Connecting to port 5432 on pooler...")
try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres.gnpsdiarmwvqhqbyetce",
        password="Rockyramboa17@",
        host="aws-0-eu-central-1.pooler.supabase.com",
        port="5432",
        connect_timeout=5,
        sslmode="require",
    )
    print("Connected!")
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        print("Query OK:", cur.fetchone())
except Exception as e:
    print("Error:", e)
