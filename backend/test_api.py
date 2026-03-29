import requests
import time

print("Starting test...")
search_payload = {
    'brands': [], 'models': [], 'samar_class_ids': [], 'trims': [], 
    'vehicle_ids': [], 'requirements': [], 'semantic_query': None,
    'offset': 0, 'limit': 20
}
try:
    search_res = requests.post('http://localhost:8000/api/scoring-search/search', json=search_payload)
    if search_res.status_code != 200:
        print("Search failed:", search_res.text)
        exit(1)
        
    vehicles = search_res.json().get('results', [])
    v_ids = [v['vehicle_id'] for v in vehicles]
    print(f"Got {len(v_ids)} vehicle IDs to query.")

    if v_ids:
        payload = {
            'vehicle_ids': v_ids,
            'duration_months': 36,
            'annual_mileage': 20000,
            'limit': 5
        }
        t0 = time.time()
        r = requests.post('http://localhost:8000/api/scoring-search/cache/batch-similar', json=payload, timeout=60)
        t1 = time.time()
        print(f"Status: {r.status_code} in {t1-t0:.2f}s")
        print(r.text[:500])
except Exception as e:
    print('Request error:', e)
print("Test done.")
