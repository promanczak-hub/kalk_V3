import psycopg2

URLS = [
    {"host": "db.gnpsdiarmwvqhqbyetce.supabase.co", "port": 5432, "user": "postgres"},
    {
        "host": "aws-0-eu-central-1.pooler.supabase.com",
        "port": 5432,
        "user": "postgres.gnpsdiarmwvqhqbyetce",
    },
    {
        "host": "aws-0-eu-central-1.pooler.supabase.com",
        "port": 6543,
        "user": "postgres.gnpsdiarmwvqhqbyetce",
    },
    {
        "host": "aws-0-eu-central-1.pooler.supabase.com",
        "port": 5432,
        "user": "postgres",
    },
]

for cfg in URLS:
    print(f"Trying {cfg} ...")
    try:
        conn = psycopg2.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password="Rockyramboa17@",
            dbname="postgres",
            connect_timeout=15,
            sslmode="require",
        )
        print("SUCCESS")
        conn.close()
        break
    except Exception as e:
        print("FAILED:", str(e).split("\n")[0])
