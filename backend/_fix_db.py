import psycopg2
import traceback


def fix():
    try:
        conn = psycopg2.connect(
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        cur = conn.cursor()

        # Check if table exists
        cur.execute(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename = 'tabela_rabaty';"
        )
        res = cur.fetchone()
        print(f"Table public.tabela_rabaty exists: {res is not None}")

        if not res:
            with open("create_tabela_rabaty.sql", "r") as f:
                sql = f.read()
            cur.execute(sql)
            conn.commit()
            print("Successfully created the tabela_rabaty table!")

        # Grant permissions
        cur.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.tabela_rabaty TO anon, authenticated, service_role;"
        )
        try:
            cur.execute(
                "GRANT USAGE, SELECT, UPDATE ON SEQUENCE public.tabela_rabaty_id_seq TO anon, authenticated, service_role;"
            )
        except Exception as se:
            print(
                "Sequence grant failed (expected if identity column creates different sequence name):",
                se,
            )
            conn.rollback()  # reset transaction state

        # Commit the permissions
        conn.commit()

        # Reload PostgREST cache
        cur.execute("NOTIFY pgrst, 'reload schema';")
        conn.commit()
        print("Grants and reload executed.")

    except Exception:
        traceback.print_exc()


fix()
