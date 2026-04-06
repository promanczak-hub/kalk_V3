import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from core.database import supabase
from api.calculator_core_routes import _resolve_engine_id, _load_engine_name_map


def debug():
    print("Fetching raw data from engines table...")
    res = supabase.table("engines").select("id, name").execute()
    for row in res.data:
        name = row["name"]
        print(f"ID: {row['id']}, Name: '{name}', Hex: {name.encode('utf-8').hex()}")

    test_input = "Benzyna (PB)"
    print(f"\nTesting input: '{test_input}', Hex: {test_input.encode('utf-8').hex()}")

    mapping = _load_engine_name_map()
    print(f"Mapping keys: {list(mapping.keys())}")

    resolved_id = _resolve_engine_id(test_input)
    print(f"Resolved ID for '{test_input}': {resolved_id}")


if __name__ == "__main__":
    debug()
