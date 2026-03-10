import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    cur = conn.cursor()
    conn.autocommit = True
    cur.execute(
        "ALTER ROLE authenticator SET pgrst.db_schemas TO 'public, graphql_public, reverse_search';"
    )
    cur.execute("NOTIFY pgrst, 'reload config';")
    print("Config reloaded successfully.")
except Exception as e:
    import traceback

    traceback.print_exc()
