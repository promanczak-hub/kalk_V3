import psycopg2
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv('d:/kalk_v3/backend/.env')
pw = os.environ.get('POSTGRES_PASSWORD', 'Rockyramboa17@')
db_url = f'postgresql://postgres.gnpsdiarmwvqhqbyetce:{urllib.parse.quote_plus(pw)}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres'
try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'rpc_get_scoring_initial_data';")
        rows = cur.fetchall()
        for row in rows:
            print(row[0])
            print('---')
except Exception as e:
    print("Error:", e)
