import urllib.request
import json

online_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"


def get_supabase(table):
    url = f"{online_url}/rest/v1/{table}?select=*"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept-Profile": "reverse_search",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


features = get_supabase("universal_features")
categories = get_supabase("universal_feature_categories")
cat_map = {c["id"]: c["display_name"] for c in categories}

print("All Categories:")
for c in categories:
    print(f"- {c['display_name']} ({c['category_key']})")

print("\nAir Conditioning Features:")
for f in features:
    if "klimatyz" in f["feature_key"] or "klimatyz" in f["display_name"].lower():
        cat_name = cat_map.get(f["category_id"], "Unknown")
        print(f"- {f['display_name']} [{f['feature_key']}] -> Category: {cat_name}")
