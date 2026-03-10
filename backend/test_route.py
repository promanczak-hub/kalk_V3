import os
from supabase import create_client

_ONLINE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co"
_ONLINE_KEY = "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9"

SUPABASE_URL = os.environ.get("SUPABASE_URL", _ONLINE_URL)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", _ONLINE_KEY)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    cats_resp = (
        sb.schema("reverse_search")
        .table("universal_feature_categories")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    print("Fetched Categories:", len(cats_resp.data))

    features_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    print("Fetched Features:", len(features_resp.data))

    categories = []
    for cat in cats_resp.data:
        cat_features = [f for f in features_resp.data if f["category_id"] == cat["id"]]
        if len(cat_features) > 0:
            print(f"Cat {cat['display_name']} has {len(cat_features)} features")
        categories.append({"id": cat["id"], "features": cat_features})
    print("Mapped Categories:", sum(len(c["features"]) for c in categories))

except Exception as e:
    print("Exception", e)
