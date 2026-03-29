import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("d:/kalk_v3/backend/.env")
db_url = os.environ.get("SUPABASE_DB_URL")
if not db_url:
    print("No SUPABASE_DB_URL found")
    exit(1)

conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()
cur.execute("NOTIFY pgrst, 'reload schema';")
print("Schema reloaded successfully.")
