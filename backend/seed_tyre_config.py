"""
Inserts required cost parameters into tyre_configurations table.
`cost_tyre_storage` - annual storage cost per set (PLN/year)
`cost_tyre_swap` - cost per tyre swap event (PLN)
"""

from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase

REQUIRED_PARAMS = [
    {
        "config_key": "cost_tyre_storage",
        "config_value": "360",
    },  # 360 PLN/rok przechowywanie
    {"config_key": "cost_tyre_swap", "config_value": "120"},  # 120 PLN przekladka
]


def main() -> None:
    # Fetch existing keys
    res = supabase.table("tyre_configurations").select("config_key").execute()
    existing = {row["config_key"] for row in (res.data or [])}
    print(f"Existing config keys: {sorted(list(existing))}")

    for param in REQUIRED_PARAMS:
        key = param["config_key"]
        if key in existing:
            print(f"  SKIP: '{key}' already exists")
        else:
            supabase.table("tyre_configurations").insert(param).execute()
            print(f"  INSERTED: '{key}' = {param['config_value']}")

    print("Done.")


if __name__ == "__main__":
    main()
