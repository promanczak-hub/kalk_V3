import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("backend/.env")


def final_setup():
    password = os.environ.get("POSTGRES_PASSWORD")
    host = "aws-1-eu-central-1.pooler.supabase.com"
    user = "postgres.gnpsdiarmwvqhqbyetce"
    dbname = "postgres"

    try:
        conn = psycopg2.connect(
            dbname=dbname, user=user, password=password, host=host, port=5432
        )
        cur = conn.cursor()

        # 1. Ensure bucket is public
        print("Ensuring bucket 'offers_excel' is public...")
        cur.execute("""
            INSERT INTO storage.buckets (id, name, public) 
            VALUES ('offers_excel', 'offers_excel', true)
            ON CONFLICT (id) DO UPDATE SET public = true;
        """)

        # 2. Add RLS policies for storage.objects (insert and select)
        print("Seting up RLS policies for 'offers_excel'...")

        # Insert
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'Public Insert'
                ) THEN
                    CREATE POLICY "Public Insert" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'offers_excel');
                END IF;
            END $$;
        """)

        # Select
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'Public Select'
                ) THEN
                    CREATE POLICY "Public Select" ON storage.objects FOR SELECT USING (bucket_id = 'offers_excel');
                END IF;
            END $$;
        """)

        conn.commit()
        print("Storage policies applied.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    final_setup()
