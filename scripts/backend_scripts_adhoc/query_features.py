import json

from core.database import supabase as sb

cats = (
    sb.schema("reverse_search")
    .table("universal_feature_categories")
    .select("id, category_key, display_name, vehicle_scope, sort_order")
    .order("sort_order")
    .execute()
)

result = []
for c in cats.data:
    feats = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("display_name, feature_type, sort_order, vehicle_scope")
        .eq("category_id", c["id"])
        .order("sort_order")
        .execute()
    )
    result.append(
        {
            "category": c["display_name"],
            "key": c["category_key"],
            "scope": c["vehicle_scope"],
            "features": [
                {
                    "name": f["display_name"],
                    "type": f["feature_type"],
                    "col": f["sort_order"],
                    "scope": f.get("vehicle_scope", "both"),
                }
                for f in feats.data
            ],
        }
    )

with open("features_dump.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"Wrote {len(result)} categories to features_dump.json")
