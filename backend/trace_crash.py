import traceback
from core.database import supabase
from core.models_features import FeatureCatalogResponse
from fastapi.encoders import jsonable_encoder

try:
    print("Fetching categories...")
    sb = supabase
    cats_resp = (
        sb.schema("reverse_search")
        .table("universal_feature_categories")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    print("Found categories:", len(cats_resp.data))

    print("Fetching features...")
    features_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    print("Found features:", len(features_resp.data))

    categories = []
    for cat in cats_resp.data:
        cat_features = [f for f in features_resp.data if f["category_id"] == cat["id"]]
        categories.append(
            {
                "id": cat["id"],
                "category_key": cat["category_key"],
                "display_name": cat["display_name"],
                "vehicle_scope": cat["vehicle_scope"],
                "features": cat_features,
            }
        )

    print("Constructing response...")
    resp = FeatureCatalogResponse(
        categories=categories,
        total_features=len(features_resp.data),
    )
    print("Encoding...")
    encoded = jsonable_encoder(resp)
    print("Success")
except Exception:
    traceback.print_exc()
