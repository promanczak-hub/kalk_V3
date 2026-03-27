import psycopg2


def apply_migration():
    # Use one of the resolved IPv4 addresses for the pooler directly to skip DNS issues
    # Host: 18.198.30.239 (aws-0-eu-central-1.pooler.supabase.com)
    # Port: 6543 (Transaction mode)
    # User: postgres.gnpsdiarmwvqhqbyetce

    DB_URL = "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@18.198.30.239:6543/postgres"

    SQL = """
    ALTER TABLE public.control_center ADD COLUMN IF NOT EXISTS cost_tyre_swap NUMERIC DEFAULT 120;
    ALTER TABLE public.control_center ADD COLUMN IF NOT EXISTS cost_tyre_storage NUMERIC DEFAULT 216;
    """

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(SQL)
            print("Successfully added tyre cost columns to control_center.")
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")


if __name__ == "__main__":
    apply_migration()
