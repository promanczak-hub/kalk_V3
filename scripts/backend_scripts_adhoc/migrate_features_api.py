import psycopg2
import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError

online_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"

# Connect to local DB to extract the successfully seeded data
local_conn_str = "postgresql://postgres:postgres@localhost:54322/postgres"

try:
    conn = psycopg2.connect(local_conn_str)
except Exception as e:
    print("Cannot connect locally:", e)
    exit(1)

categories = []
features = []

with conn.cursor() as cur:
    # Read categories
    cur.execute(
        "SELECT id, category_key, display_name, vehicle_scope, sort_order FROM reverse_search.universal_feature_categories"
    )
    for row in cur.fetchall():
        categories.append(
            {
                "id": row[0],
                "category_key": row[1],
                "display_name": row[2],
                "vehicle_scope": row[3],
                "sort_order": row[4],
            }
        )

    # Read features
    cur.execute(
        "SELECT id, category_id, feature_key, display_name, data_type, metadata, vehicle_scope, is_filterable, sort_order, is_active FROM reverse_search.universal_features"
    )
    for row in cur.fetchall():
        features.append(
            {
                "id": row[0],
                "category_id": row[1],
                "feature_key": row[2],
                "display_name": row[3],
                "data_type": row[4],
                "metadata": row[5] if row[5] else None,
                "vehicle_scope": row[6],
                "is_filterable": row[7],
                "sort_order": row[8],
                "is_active": row[9],
            }
        )

conn.close()
print(
    f"Extracted {len(categories)} categories and {len(features)} features from local DB."
)


def post_to_supabase(table, data):
    url = f"{online_url}/rest/v1/{table}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal, resolution=merge-duplicates",
    }

    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Uploaded {len(data)} to {table}: HTTP {response.status}")
    except HTTPError as e:
        print(f"Upload error to {table}: {e.code} - {e.read().decode('utf-8')}")


if categories:
    post_to_supabase("universal_feature_categories", categories)
if features:
    # Because of URL limits and sizes, break features into batches of 50
    for i in range(0, len(features), 50):
        batch = features[i : i + 50]
        post_to_supabase("universal_features", batch)
