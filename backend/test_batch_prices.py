import urllib.request
import json
import urllib.error

url = "http://127.0.0.1:8000/api/scoring-search/cache/batch-prices"
payload = {
    "vehicle_ids": ["011fd704-5f53-4813-afd2-fc53ff9d2cdb"],
    "duration_months_min": 24,
    "duration_months_max": 60,
    "annual_mileage_min": 10000,
    "annual_mileage_max": 40000,
}
req = urllib.request.Request(
    url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
)

try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print("ERROR:", e.read().decode())
