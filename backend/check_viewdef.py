import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def get_view_def():
    # Local supabase default credentials
    # postgresql://postgres:postgres@localhost:54322/postgres
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("SELECT pg_get_viewdef('fleet_management_view', true);")
    res = cur.fetchone()
    if res:
        print("VIEW DEF:\n", res[0])
    cur.close()
    conn.close()


if __name__ == "__main__":
    get_view_def()
