import psycopg2
import os
from dotenv import load_dotenv

# Load backend .env
load_dotenv("backend/.env")


def run_migration():
    password = os.getenv("POSTGRES_PASSWORD", "Rockyramboa17@")
    # TRY AWS-1
    host = "aws-1-eu-central-1.pooler.supabase.com"
    user = "postgres.gnpsdiarmwvqhqbyetce"
    dbname = "postgres"
    port = "6543"

    try:
        print(f"Connecting to {host}:{port} as {user}...")
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname,
            port=port,
            sslmode="require",
            connect_timeout=10,
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
        print(f"Migration failed with host {host}: {e}")


if __name__ == "__main__":
    run_migration()
