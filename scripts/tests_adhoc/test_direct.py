from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

payload1 = {"search_query": "diesel", "filters": [], "limit": 10, "offset": 0}

payload2 = {
    "search_query": "",
    "filters": [{"feature_key": "klimatyzacja_automatyczna", "value_bool": True}],
    "limit": 10,
    "offset": 0,
    "price_months": 48,
    "price_mileage": 20000,
    "price_min": 1000,
    "price_max": 9000,
}

print("=== TEST 1: Text search 'diesel' ===")
r = client.post("/api/features/search", json=payload1)
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Total count:", data.get("total_count"))
    for res in data.get("results", [])[:2]:
        print(
            f"- {res.get('brand')} {res.get('model')} (Score: {res.get('match_score')}, Price: {res.get('price_netto')})"
        )
else:
    print("Response text:", r.text[:200])

print("\n=== TEST 2: Feature search (Klimatyzacja automatyczna + Price limit) ===")
r = client.post("/api/features/search", json=payload2)
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Total count:", data.get("total_count"))
    for res in data.get("results", [])[:2]:
        print(
            f"- {res.get('brand')} {res.get('model')} (Score: {res.get('match_score')}, Price: {res.get('price_netto')})"
        )
else:
    print("Response text:", r.text[:200])
