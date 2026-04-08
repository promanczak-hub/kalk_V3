import os
import psycopg2

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    print("--- Feature Categories ---")
    cur.execute(
        "SELECT id, name, sort_order FROM reverse_search.feature_categories ORDER BY sort_order"
    )
    cats = cur.fetchall()
    for cat in cats:
        cat_id, cat_name, cat_sort = cat
        print(f"[{cat_sort}] {cat_name} (ID: {cat_id})")
        cur.execute(
            "SELECT feature_key, display_name, feature_type, sort_order FROM reverse_search.universal_features WHERE category_id = %s ORDER BY sort_order, display_name",
            (cat_id,),
        )
        features = cur.fetchall()
        for f in features:
            f_key, f_name, f_type, f_sort = f
            print(f"  - {f_name} ({f_key}): {f_type}")
    cur.close()
    conn.close()
except Exception:
    import traceback

    traceback.print_exc()
