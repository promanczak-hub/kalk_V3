import os
import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    cur = conn.cursor()
    cur.execute(
        "SELECT id, stan_json, status FROM ltr_kalkulacje WHERE status='completed' ORDER BY created_at DESC LIMIT 1;"
    )
    res = cur.fetchone()
    if res:
        print(f"Calculation ID: {res[0]}")
        stan = res[1] or {}
        print("Root keys:", list(stan.keys()))
        if "samochod" in stan:
            print("samochod keys:", list(stan["samochod"].keys()))
        if "pojazd" in stan:
            print("pojazd keys:", list(stan["pojazd"].keys()))
        if "vertex_data" in stan:
            print("vertex_data keys:", list(stan["vertex_data"].keys()))

        print("JSON snippet:")
        print(json.dumps(stan, indent=2, ensure_ascii=False)[:1000])

        # also search for exterior_color anywhere
        def find_key(d, key):
            if isinstance(d, dict):
                if key in d:
                    yield d[key]
                for k, v in d.items():
                    yield from find_key(v, key)
            elif isinstance(d, list):
                for item in d:
                    yield from find_key(item, key)

        colors = list(find_key(stan, "exterior_color"))
        eqs = list(find_key(stan, "equipment_list"))

        print(f"\nFound exterior_colors anywhere: {colors}")
        print(f"Found equipment_lists anywhere: {eqs}")
    else:
        print("No completed calculations found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
