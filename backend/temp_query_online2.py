import json
import psycopg2
from psycopg2.extras import RealDictCursor


def fetch_bmw_x3_online():
    # Use the connection string provided by the user.
    # Password bracket encoded or literal? Usually literal without brackets or with percent encoding.
    # The user wrote: postgresql://postgres:[Rockyramboa17@]@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres
    # The brackets are probably just to highlight the password. Let's use it as: Rockyramboa17@
    # But wait, @ in password will break URL parsing. It must be URL encoded as %40
    db_url = "postgresql://postgres:Rockyramboa17%40@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, json_data->>'id' as json_id, json_data->>'model' as model, 
                   json_data->>'make' as make, json_data->>'trim' as trim, json_data->>'vin' as vin,
                   samar_category, engine_class, body_type, drive_type,
                   json_data
            FROM fleet_management_view
            WHERE json_data->>'model' ILIKE '%X3%'
               OR json_data->>'vin' IN ('WBA11GR0309349983', 'WBA11GR0609352697')
        """)
        rows = cur.fetchall()

        out = [dict(r) for r in rows]
        with open("d:/kalk_v3/backend/online_bmw_x3.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False, default=str)

        print(
            f"Pobrano {len(out)} rekordów BMW X3 z bazy ONLINE i zapisano do online_bmw_x3.json"
        )
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Błąd: {e}")


if __name__ == "__main__":
    fetch_bmw_x3_online()
