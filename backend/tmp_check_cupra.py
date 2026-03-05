import sys

sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase


def run():
    res = supabase.table("vehicle_synthesis").select("synthesis_data").execute()
    for row in res.data:
        stan = row.get("synthesis_data", {})
        if not stan:
            continue
        cs = stan.get("card_summary", {})
        if not cs:
            continue
        print(f"Vehicle: {cs.get('brand', '')} {cs.get('model', '')}")


if __name__ == "__main__":
    run()
