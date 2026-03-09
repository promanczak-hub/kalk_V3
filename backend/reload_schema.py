import psycopg2

conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
conn.autocommit = True
cur = conn.cursor()
cur.execute("GRANT SELECT ON body_types TO anon;")
cur.execute("GRANT SELECT ON body_types TO authenticated;")
cur.execute("GRANT SELECT ON body_types TO service_role;")
cur.execute("NOTIFY pgrst, 'reload schema';")
print("Grants applied and schema reloaded!")
