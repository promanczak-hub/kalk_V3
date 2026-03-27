import requests
import json

url = "http://127.0.0.1:8000/api/calculate-matrix"
payload = {
    "vehicle_id": "f6e4ed0a-1273-43a5-b6e0-fd4cf6689d81",
    "base_price_net": 120000.0,
    "samar_category": "Lekkie dostawcze - VAN",
    "engine_name": "Benzyna (PB)",
    "srednica_felgi": 16,
    "z_oponami": True,
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
