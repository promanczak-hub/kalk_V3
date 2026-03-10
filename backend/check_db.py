import psycopg2
import sys
import json

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=54322,
        user="postgres",
        password="postgres",
        dbname="postgres",
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT brand, model, trim_level, configuration_code, body_style, powertrain FROM fleet_management_view WHERE model ILIKE '%Caddy%';"
    )
    colnames = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    if not rows:
        print("No Caddy found")
    else:
        for row in rows:
            print(
                json.dumps(
                    dict(
                        zip(colnames, [str(v) if v is not None else None for v in row])
                    ),
                    indent=2,
                    ensure_ascii=False,
                )
            )
except Exception as e:
    print(f"Error: {e}")
