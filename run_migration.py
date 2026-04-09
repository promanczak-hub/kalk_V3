import psycopg2

def main():
    try:
        conn = psycopg2.connect(
            host="aws-0-eu-central-1.pooler.supabase.com",
            port=6543,
            user="postgres.gnpsdiarmwvqhqbyetce",
            password="Rockyramboa17@",
            dbname="postgres",
            sslmode="require"
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("SUCCESS:", cur.fetchone())
        
        # Read the file and execute the migration
        with open(r"d:\kalk_v3\supabase\migrations\20260410000000_add_requirements_to_alternatives.sql", "r", encoding="utf-8") as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()
        print("MIGRATION APPLIED SUCESSFULLY.")
        cur.close()
        conn.close()
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    main()
