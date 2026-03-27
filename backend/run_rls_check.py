import psycopg2

db_url = "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"


def check_rls():
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        query = """
        SELECT relname 
        FROM pg_class 
        WHERE relnamespace = 'public'::regnamespace 
          AND relkind = 'r' 
          AND NOT relrowsecurity;
        """
        cur.execute(query)
        tables_without_rls = [r[0] for r in cur.fetchall()]
        print("Tabele bez włączonego RLS:", tables_without_rls)
        cur.close()
        conn.close()
    except Exception as e:
        print("Błąd:", e)


if __name__ == "__main__":
    check_rls()
