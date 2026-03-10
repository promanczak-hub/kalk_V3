import urllib.request
import json
import sys

req = urllib.request.Request("http://localhost:8000/api/features/catalog", method="GET")
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"Categories: {len(data.get('categories', []))}")
        print(f"Features: {len(data.get('features', []))}")
        if data.get("features"):
            print("Sample Feature:")
            print(json.dumps(data["features"][0], indent=2))
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, "read"):
        print(f"Response: {e.read().decode('utf-8')}")
