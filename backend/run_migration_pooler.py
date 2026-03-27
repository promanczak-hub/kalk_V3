import psycopg2

pooler_conn_string = "postgresql://postgres:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"


def run_migration():
    try:
        conn = psycopg2.connect(pooler_conn_string)
        cur = conn.cursor()
        print("Połączono. Wykonuję ALTER TABLE...")

        # SQL to add the missing columns
        sql = """
        ALTER TABLE public.samar_classes
        ADD COLUMN IF NOT EXISTS base_mileage_km NUMERIC DEFAULT 15000,
        ADD COLUMN IF NOT EXISTS mileage_threshold_km NUMERIC DEFAULT 140000,
        ADD COLUMN IF NOT EXISTS base_period_months INTEGER DEFAULT 48;
        """
        cur.execute(sql)
        conn.commit()
        print("Sukces! Kolumny zostały dodane za pomocą IPv4 Poolera.")

        # Verify
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'samar_classes';
        """)
        cols = cur.fetchall()
        print("Obecne kolumny w samar_classes:", [c[0] for c in cols])
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Błąd podczas wykonywania zapytania do poolera: {e}")


if __name__ == "__main__":
    run_migration()
