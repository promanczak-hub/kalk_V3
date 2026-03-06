"""Add AC/OC default columns to control_center."""

import sys

sys.path.insert(0, ".")
import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=54322,
    dbname="postgres",
    user="postgres",
    password="postgres",
)
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
    ALTER TABLE control_center
    ADD COLUMN IF NOT EXISTS ins_default_ac_rate NUMERIC DEFAULT 0.015;
""")
cur.execute("""
    ALTER TABLE control_center
    ADD COLUMN IF NOT EXISTS ins_default_oc_rate NUMERIC DEFAULT 1476.0;
""")

cur.execute("""
    UPDATE control_center
    SET ins_default_ac_rate = 0.015,
        ins_default_oc_rate = 1476.0
    WHERE id = 1;
""")

cur.execute(
    "SELECT ins_default_ac_rate, ins_default_oc_rate FROM control_center WHERE id = 1;"
)
row = cur.fetchone()
print(f"AC rate: {row[0]}, OC rate: {row[1]}")

cur.close()
conn.close()
print("Done!")
