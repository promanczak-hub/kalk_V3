import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    print("Testing if metadata exists...")
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='universal_features';"
    )
    cols = [r[0] for r in cur.fetchall()]
    print("Columns:", cols)

    if "metadata" not in cols:
        print("Adding metadata column...")
        cur.execute(
            "ALTER TABLE reverse_search.universal_features ADD COLUMN IF NOT EXISTS metadata jsonb;"
        )
        print("Added metadata column.")
    else:
        print("Metadata column already exists.")

    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
