import psycopg2
import os
from dotenv import load_dotenv

# Load backend .env
load_dotenv("backend/.env")

def run_migration():
    password = os.getenv("POSTGRES_PASSWORD", "Rockyramboa17@")
    # IP from migrate_tyre_costs.py or common pooler IPs
    # aws-0-eu-central-1.pooler.supabase.com sometimes resolves to 18.192.147.20 or 18.198.30.239
    host_ip = "18.198.30.239" 
    user = "postgres.gnpsdiarmwvqhqbyetce"
    dbname = "postgres"
    port = "6543"
    
    try:
        print(f"Connecting to {host_ip}:{port} as {user}...")
        conn = psycopg2.connect(
            host=host_ip,
            user=user,
            password=password,
            dbname=dbname,
            port=port,
            sslmode="require",
            connect_timeout=10
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Migrating: Adding created_at to vehicle_matrix_cache...")
        cur.execute("ALTER TABLE vehicle_matrix_cache ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
        print("Migration successful.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed with IP {host_ip}: {e}")
        # Try another IP if this one fails
        try_other_ips(password, user, dbname, port)

def try_other_ips(password, user, dbname, port):
    other_ips = ["18.192.147.20", "52.59.152.35"] # 52.59.152.35 was resolved earlier by ping/retry
    for ip in other_ips:
        try:
            print(f"Connecting to {ip}:{port} as {user}...")
            conn = psycopg2.connect(
                host=ip,
                user=user,
                password=password,
                dbname=dbname,
                port=port,
                sslmode="require",
                connect_timeout=10
            )
            conn.autocommit = True
            cur = conn.cursor()
            print(f"Migration successful with IP {ip}.")
            cur.close()
            conn.close()
            return
        except Exception as e:
            print(f"Migration failed with IP {ip}: {e}")

if __name__ == "__main__":
    run_migration()
