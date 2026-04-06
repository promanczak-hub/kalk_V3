import json
from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    res = supabase.table("tab_okres_final").select("samar_class, engine_type").execute()
    c = set(str(r.get("samar_class", "")) for r in res.data)
    e = set(str(r.get("engine_type", "")) for r in res.data)

    with open("dump.json", "w", encoding="utf-8") as f:
        json.dump(
            {"c": sorted(list(c)), "e": sorted(list(e))},
            f,
            indent=2,
            ensure_ascii=False,
        )
    print("SAVED DUMP.JSON")


if __name__ == "__main__":
    main()
