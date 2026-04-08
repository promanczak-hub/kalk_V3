import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    print("--- Feature Categories ---")
    cats_response = (
        supabase.schema("reverse_search")
        .table("universal_feature_categories")
        .select("id, display_name, sort_order")
        .order("sort_order")
        .execute()
    )
    cats = cats_response.data
    for cat in cats:
        cat_id = cat["id"]
        print(f"[{cat['sort_order']}] {cat['display_name']} (ID: {cat_id})")

        feat_response = (
            supabase.schema("reverse_search")
            .table("universal_features")
            .select("feature_key, display_name, feature_type, sort_order")
            .eq("category_id", cat_id)
            .order("sort_order")
            .order("display_name")
            .execute()
        )
        features = feat_response.data
        for f in features:
            print(f"  - {f['display_name']} ({f['feature_key']}): {f['feature_type']}")
except Exception:
    import traceback

    traceback.print_exc()
