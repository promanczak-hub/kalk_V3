import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
url = os.getenv("POSTGRES_URL")
if not url:
    print("POSTGRES_URL not found in .env")
    exit(1)

try:
    conn = psycopg2.connect(url)
    with conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE public.body_types ADD COLUMN IF NOT EXISTS utrata_wartosci NUMERIC DEFAULT 0;"
        )
        cur.execute(
            "COMMENT ON COLUMN public.body_types.utrata_wartosci IS 'Bazowa utrata wartości (korekta RV) dla danego typu nadwozia.';"
        )
        conn.commit()
    print("Migration applied successfully")
except Exception as e:
    print(f"Error applying migration: {e}")
finally:
    if "conn" in locals():
        conn.close()
