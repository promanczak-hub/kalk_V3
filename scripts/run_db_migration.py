import psycopg2
import os
from dotenv import load_dotenv

# Load backend .env
load_dotenv("backend/.env")


def run_migration():
    password = os.getenv("POSTGRES_PASSWORD", "Rockyramboa17@")
    host = "aws-0-eu-central-1.pooler.supabase.com"
    user = "postgres.gnpsdiarmwvqhqbyetce"
    dbname = "postgres"

    try:
        conn = psycopg2.connect(
            host=host, user=user, password=password, dbname=dbname, sslmode="require"
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("Migrating: Adding created_at to vehicle_matrix_cache...")
        cur.execute(
            "ALTER TABLE vehicle_matrix_cache ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();"
        )
        print("Migration successful.")

        cur.close()
        conn.close()
    except Exception as e:
        print("Migration failed:", str(e))


if __name__ == "__main__":
    run_migration()
