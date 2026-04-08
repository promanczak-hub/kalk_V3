import sys
from dotenv import load_dotenv

load_dotenv(r"d:\kalk_v3\backend\.env")
sys.path.insert(0, r"d:\kalk_v3\backend")
from core.database import supabase
from api.calculator_core_routes import readiness_check

print("Fetching all vehicles...")
vehicles = (
    supabase.table("vehicle_synthesis")
    .select("id, brand, model, synthesis_data")
    .execute()
    .data
)
print(f"Found {len(vehicles)} vehicles. Checking readiness...")

fails = 0
for v in vehicles:
    syn = v.get("synthesis_data") or {}
    ai = syn.get("mapped_ai_data") or {}

    # readiness_check args
    samar_class_name = ai.get("samar_category")
    engine_name = ai.get("engine_class")
    brand_name = v.get("brand")
    body_type_name = ai.get("body_type")

    visual = syn.get("visual_identity") or {}
    paint_type_name = visual.get("paint_type")

    zabudowa = None  # TODO check if needed

    if not samar_class_name or not engine_name:
        fails += 1
        print(
            f"[{v['id']}] {brand_name} {v['model']} - BRAK samar_class_name LUB engine_name w mapped_ai_data!"
        )
        continue

    try:
        res = readiness_check(
            samar_class_name=samar_class_name,
            engine_name=engine_name,
            brand_name=brand_name,
            vehicle_id=v["id"],
            body_type_name=body_type_name,
            paint_type_name=paint_type_name,
            zabudowa_type_id=zabudowa,
        )
        if not res.get("is_ready"):
            fails += 1
            print(
                f"[{v['id']}] {brand_name} {v['model']} - NOT READY: {res.get('reasons')}"
            )
    except Exception as e:
        fails += 1
        print(f"[{v['id']}] {brand_name} {v['model']} - EXCEPTION: {e}")

print(f"Total fails: {fails} / {len(vehicles)}")
