import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("backend/.env")


def create_bucket():
    password = os.environ.get("POSTGRES_PASSWORD")
    host = "aws-1-eu-central-1.pooler.supabase.com"
    user = "postgres.gnpsdiarmwvqhqbyetce"
    dbname = "postgres"

    try:
        conn = psycopg2.connect(
            dbname=dbname, user=user, password=password, host=host, port=5432
        )
        cur = conn.cursor()
        print("Checking storage.buckets...")
        cur.execute("SELECT id FROM storage.buckets WHERE id = 'offers_excel';")
        res = cur.fetchone()
        if res:
            print(f"Bucket {res[0]} already exists.")
        else:
            print("Bucket offers_excel does not exist. Attempting direct DB insert...")
            try:
                # Direct insert into storage.buckets if we have permission
                cur.execute("""
                    INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) 
                    VALUES ('offers_excel', 'offers_excel', true, NULL, NULL)
                    ON CONFLICT (id) DO NOTHING;
                """)
                conn.commit()
                print("Bucket entry created in storage.buckets.")
            except Exception as e:
                print(f"Failed to insert into storage.buckets: {e}")
                conn.rollback()

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    create_bucket()
