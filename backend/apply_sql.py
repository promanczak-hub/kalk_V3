import psycopg2

# Default local supabase connection string
DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"


def apply_migration():
    sql = """
    ALTER TABLE control_center
    ADD COLUMN IF NOT EXISTS ins_nnw_annual_rate NUMERIC DEFAULT 150.0,
    ADD COLUMN IF NOT EXISTS ins_ass_annual_rate NUMERIC DEFAULT 200.0,
    ADD COLUMN IF NOT EXISTS ins_green_card_annual_rate NUMERIC DEFAULT 50.0;
    """
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
        print("Migration applied successfully!")
    except Exception as e:
        print(f"Error applying migration: {e}")
    finally:
        if "conn" in locals() and conn:
            conn.close()


if __name__ == "__main__":
    apply_migration()
