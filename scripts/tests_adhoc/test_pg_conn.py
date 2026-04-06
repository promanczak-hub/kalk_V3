import psycopg2
import urllib.parse

password = urllib.parse.quote_plus("Rockyramboa17@")
conn_string = f"postgresql://postgres:{password}@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"

try:
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("Connection successful!")

    # Check if columns exist
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'samar_classes';
    """)
    cols = cur.fetchall()
    print("Columns in samar_classes:", cols)

    conn.close()
except Exception as e:
    print("Connection failed:", e)
