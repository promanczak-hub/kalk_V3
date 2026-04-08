import sys
import os

sys.path.append(os.path.abspath("."))
from core.database import supabase

result = (
    supabase.schema("reverse_search")
    .table("universal_features")
    .select(
        "technical_key, feature_tier, is_filterable, is_tender_criteria, is_comparable"
    )
    .eq("feature_tier", "CORE")
    .execute()
)
print(f"CORE cechy: {len(result.data)}")
all_ok = all(
    r["is_filterable"] and r["is_tender_criteria"] and r["is_comparable"]
    for r in result.data
)
print(f"Wszystkie flagi OK: {all_ok}")
if not all_ok:
    for r in result.data:
        if not (r["is_filterable"] and r["is_tender_criteria"] and r["is_comparable"]):
            print(
                f"  ❌ {r['technical_key']}: F={r['is_filterable']} T={r['is_tender_criteria']} C={r['is_comparable']}"
            )

# Sprawdz kilka EXTENDED
ext_check = (
    supabase.schema("reverse_search")
    .table("universal_features")
    .select("technical_key, is_filterable, is_comparable")
    .in_(
        "technical_key",
        [
            "kamera_cofania",
            "aktywny_tempomat",
            "klimatyzacja_automatyczna",
            "gps_nawigacja_satelitarna",
        ],
    )
    .execute()
)
print("\nEXTENDED (sample):")
for r in ext_check.data:
    print(f"  {r['technical_key']}: F={r['is_filterable']} C={r['is_comparable']}")
