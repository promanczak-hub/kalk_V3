import logging
import json
import traceback
from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.DEBUG)


def main():
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    fabias = []
    for v in res.data:
        sd_str = json.dumps(v.get("synthesis_data", {}))
        if "Skoda" in sd_str and "Fabia" in sd_str:
            fabias.append(v["id"])

    print(f"Total Fabias to refresh: {len(fabias)}")

    try:
        refresh_matrix_cache_for_vehicles(fabias)
    except Exception:
        traceback.print_exc()

    print("All Fabias refreshed. Check logs above.")


if __name__ == "__main__":
    main()
