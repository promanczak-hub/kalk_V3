import urllib.request
import urllib.error
import json
import traceback

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/features/catalog") as r:
        data = json.loads(r.read().decode("utf-8"))

    print("Categories:", len(data.get("categories", [])))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Response:", e.read().decode("utf-8"))
except Exception as e:
    print("Error:")
    traceback.print_exc()
