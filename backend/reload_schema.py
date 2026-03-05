import psycopg2

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:54322/postgres")
conn.autocommit = True
cur = conn.cursor()
cur.execute("NOTIFY pgrst, 'reload schema'")
print("Schema reloaded")
