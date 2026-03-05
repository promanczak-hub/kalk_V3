import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    res = conn.execute(
        text(
            "SELECT synthesis_data FROM vehicle_synthesis WHERE synthesis_data::text LIKE '%SP65VRGF%' ORDER BY created_at DESC LIMIT 1;"
        )
    ).fetchone()
    if res:
        with open("sp65vrgf_debug.json", "w", encoding="utf-8") as f:
            json.dump(res[0], f, indent=2, ensure_ascii=False)
        print("SAVED to sp65vrgf_debug.json")
    else:
        print("NOT FOUND")
