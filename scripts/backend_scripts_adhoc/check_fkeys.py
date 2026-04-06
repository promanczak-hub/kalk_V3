import psycopg2
import sys

def main():
    try:
        conn = psycopg2.connect(
            host="db.gnpsdiarmwvqhqbyetce.supabase.co",
            database="postgres",
            user="postgres",
            password="ROckyramboa17@",
            port=5432,
        )
        cur = conn.cursor()

        cur.execute("""
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'tab_okres_final';
        """)
        rows = cur.fetchall()
        print("CONSTRAINTS ON tab_okres_final:")
        for r in rows:
            print(r)

        cur.close()
        conn.close()
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    main()
