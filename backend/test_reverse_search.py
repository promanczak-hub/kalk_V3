import requests

url = "http://127.0.0.1:8000/api/features/search"

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
r = requests.post(url, json=payload1)
print("Status:", r.status_code)
try:
    data = r.json()
    print("Total count:", data.get("total_count"))
    if data.get("results"):
        print("Top 2 results:")
        for res in data["results"][:2]:
            print(
                f"- {res.get('brand')} {res.get('model')} (Score: {res.get('match_score')}, Price: {res.get('price_netto')})"
            )
except Exception as e:
    print("Error parsing JSON:", e)
    print("Response text:", r.text[:200])

print("\n=== TEST 2: Feature search (Klimatyzacja automatyczna + Price limit) ===")
r = requests.post(url, json=payload2)
print("Status:", r.status_code)
try:
    data = r.json()
    print("Total count:", data.get("total_count"))
    if data.get("results"):
        print("Top 2 results:")
        for res in data["results"][:2]:
            print(
                f"- {res.get('brand')} {res.get('model')} (Score: {res.get('match_score')}, Price: {res.get('price_netto')})"
            )
except Exception as e:
    print("Error parsing JSON:", e)
    print("Response text:", r.text[:200])
