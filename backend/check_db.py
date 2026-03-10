import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reverse_search.universal_feature_categories;")
    print("Categories:", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM reverse_search.universal_features;")
    print("Features:", cur.fetchone()[0])
    cur.execute(
        "SELECT COUNT(*) FROM reverse_search.universal_features WHERE is_active=true AND is_filterable=true;"
    )
    print("Active filterable features:", cur.fetchone()[0])
except Exception as e:
    print("Error:", e)
