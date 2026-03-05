import os
import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    cur = conn.cursor()
    cur.execute(
        "SELECT id, numer_kalkulacji, stan_json, status FROM ltr_kalkulacje WHERE numer_kalkulacji ILIKE '%SP65VRGF%' OR stan_json::text ILIKE '%SP65VRGF%' OR dane_pojazdu ILIKE '%SP65VRGF%';"
    )
    rows = cur.fetchall()

    if not rows:
        print("No calculations for SP65VRGF found.")
    else:
        for res in rows:
            print(
                f"\n--- Calculation ID: {res[0]}, Numer: {res[1]} (Status: {res[3]}) ---"
            )
            stan = res[2] or {}

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

            print(f"Found exterior_colors anywhere: {colors}")

            if eqs and eqs[0]:
                for eq in eqs[0]:
                    name = eq.get("name", "") if isinstance(eq, dict) else str(eq)
                    if (
                        "Void" in str(name)
                        or "5.476" in str(name)
                        or "476" in str(name)
                        or "Lakier" in str(name)
                    ):
                        print(f"Matching equipment: {eq}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
