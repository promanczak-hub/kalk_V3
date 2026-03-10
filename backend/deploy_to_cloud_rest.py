import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError
import re
import ast

online_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"


def post_to_supabase(table, data):
    url = f"{online_url}/rest/v1/{table}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal, resolution=merge-duplicates",
        "Content-Profile": "reverse_search",
        "Accept-Profile": "reverse_search",
    }
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Uploaded {len(data)} to {table}: HTTP {response.status}")
    except HTTPError as e:
        print(f"Upload error to {table}: {e.code} - {e.read().decode('utf-8')}")


with open("d:/kalk_v3/seed_features_with_metadata.sql", "r", encoding="utf-8") as f:
    sql = f.read()

categories = []
features = []

cat_pattern = re.compile(
    r"INSERT INTO reverse_search\.universal_feature_categories \(id, category_key, display_name, vehicle_scope, sort_order\) VALUES \('([^']+)', '([^']+)', '([^']+)', '([^']+)', (\d+)\);"
)
for match in cat_pattern.finditer(sql):
    categories.append(
        {
            "id": match.group(1),
            "category_key": match.group(2),
            "display_name": match.group(3).replace("''", "'"),
            "vehicle_scope": match.group(4),
            "sort_order": int(match.group(5)),
        }
    )

feat_pattern = re.compile(
    r"INSERT INTO reverse_search\.universal_features \(id, category_id, feature_key, display_name, feature_type, metadata, vehicle_scope, is_filterable, sort_order\) VALUES \('([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)'::jsonb, '([^']+)', (true|false), (\d+)\);"
)
for match in feat_pattern.finditer(sql):
    meta_str = match.group(6).replace("''", "'")
    features.append(
        {
            "id": match.group(1),
            "category_id": match.group(2),
            "feature_key": match.group(3),
            "display_name": match.group(4).replace("''", "'"),
            "feature_type": match.group(5),
            "metadata": json.loads(meta_str),
            "vehicle_scope": match.group(7),
            "is_filterable": match.group(8) == "true",
            "sort_order": int(match.group(9)),
        }
    )

print(
    f"Parsed {len(categories)} categories and {len(features)} features for deployment."
)

if categories:
    post_to_supabase("universal_feature_categories", categories)

if features:
    for i in range(0, len(features), 50):
        batch = features[i : i + 50]
        post_to_supabase("universal_features", batch)
