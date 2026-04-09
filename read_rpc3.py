import psycopg2

def main():
    conn = psycopg2.connect("postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_get_functiondef(oid) 
        FROM pg_proc 
        WHERE proname = 'rpc_get_alternatives_semantic';
    """)
    for row in cur.fetchall():
        print("----- FUNCTION DEF -----")
        print(row[0])
        print("------------------------")
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
