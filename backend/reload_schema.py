import os
import psycopg2

conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
conn.autocommit = True
cur = conn.cursor()
cur.execute("GRANT SELECT ON body_types TO anon;")
cur.execute("GRANT SELECT ON body_types TO authenticated;")
cur.execute("GRANT SELECT ON body_types TO service_role;")
cur.execute("NOTIFY pgrst, 'reload schema';")
print("Grants applied and schema reloaded!")
