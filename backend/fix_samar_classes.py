import psycopg2
import urllib.parse

# URL encode the password since it contains special characters (@)
password = urllib.parse.quote_plus("Rockyramboa17@")

# Try IPv4 pooler first (avoids Windows IPv6 WSAEINVAL error)
pooler_conn_string = f"postgresql://postgres.gnpsdiarmwvqhqbyetce:{password}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

# Try the direct IPv6 connection provided by user as fallback
direct_conn_string = f"postgresql://postgres:{password}@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"


def run_migration():
    conn = None
    try:
        print("Tróją połączenie przez Pooler (IPv4)...")
        conn = psycopg2.connect(pooler_conn_string)
    except Exception as e:
        print(f"Pooler failed: {e}")
        try:
            print("Próba bezpośredniego połączenia IPv6 (port 5432)...")
            conn = psycopg2.connect(direct_conn_string)
        except Exception as e2:
            print(f"Błąd połączenia: {e2}")
            return

    try:
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
        print("Sukces! Kolumny zostały dodane.")

        # Verify
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'samar_classes';
        """)
        cols = cur.fetchall()
        print("Obecne kolumny w samar_classes:", [c[0] for c in cols])

    except Exception as e:
        print(f"Błąd podczas wykonywania zapytania: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()
