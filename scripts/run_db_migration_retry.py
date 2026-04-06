import psycopg2
import os
from dotenv import load_dotenv

# Load backend .env
load_dotenv("backend/.env")

def try_host(host, user, password, dbname):
    print(f"Trying host: {host}, user: {user}...")
    try:
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname,
            sslmode="require",
            connect_timeout=10
        )
        conn.autocommit = True
        print(f"Connection success to {host}")
        return conn
    except Exception as e:
        print(f"Connection failed to {host}: {e}")
        return None

def run_migration():
    password = os.getenv("POSTGRES_PASSWORD", "Rockyramboa17@")
    dbname = "postgres"
    project_ref = "gnpsdiarmwvqhqbyetce"
    
    hosts = [
        ("db.gnpsdiarmwvqhqbyetce.supabase.co", "postgres"),
        (f"aws-0-eu-central-1.pooler.supabase.com", f"postgres.{project_ref}"),
        (f"aws-0-eu-west-1.pooler.supabase.com", f"postgres.{project_ref}"),
        (f"aws-0-us-east-1.pooler.supabase.com", f"postgres.{project_ref}"),
    ]
    
    conn = None
    for host, user in hosts:
        conn = try_host(host, user, password, dbname)
        if conn:
            break
            
    if not conn:
        print("ALL CONNECTION ATTEMPTS FAILED.")
        return

    try:
        cur = conn.cursor()
        print("Migrating: Adding created_at to vehicle_matrix_cache...")
        cur.execute("ALTER TABLE vehicle_matrix_cache ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
        print("Migration successful.")
        cur.close()
        conn.close()
    except Exception as e:
        print("Migration execution failed:", str(e))

if __name__ == "__main__":
    run_migration()
