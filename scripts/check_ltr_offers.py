import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("backend/.env")

def check_table():
    password = os.environ.get("POSTGRES_PASSWORD")
    host = "aws-1-eu-central-1.pooler.supabase.com"
    user = "postgres.gnpsdiarmwvqhqbyetce"
    dbname = "postgres"
    
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=5432
        )
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ltr_offers';")
        res = cur.fetchone()
        if res:
            print(f"Table {res[0]} exists.")
        else:
            print("Table ltr_offers does not exist. Creating it...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ltr_offers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    client_name TEXT,
                    client_nip TEXT,
                    total_calculations INTEGER,
                    offer_snapshot JSONB,
                    excel_file_path TEXT
                );
            """)
            conn.commit()
            print("Table ltr_offers created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table()
