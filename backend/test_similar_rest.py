import requests
import json
import uuid

ref = "gnpsdiarmwvqhqbyetce"
token = "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9"
url = f"https://api.supabase.com/v1/projects/{ref}/database/query"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

q1 = """
SELECT id, brand, model, (synthesis_data->'mapped_ai_data'->>'body_style') as body, 
       COALESCE((synthesis_data->'card_summary'->>'base_price')::numeric, 0) as price
FROM public.vehicle_synthesis 
WHERE brand ILIKE 'Skoda' AND model ILIKE 'Superb' 
LIMIT 1;
"""
resp = requests.post(url, headers=headers, json={"query": q1})
data = resp.json()

superb_id = data[0]["id"]
print(f"Found Superb ID: {superb_id} Body: {data[0].get('body')} Price: {data[0].get('price')}")

q2 = f"SELECT * FROM reverse_search.rpc_get_similar_vehicles('{superb_id}'::uuid, 10);"
resp2 = requests.post(url, headers=headers, json={"query": q2})
results = resp2.json()

print(f"\nSimilar vehicles:")
for r in results:
    s_score = r.get("similarity_score_pct")
    s_brand = r.get("brand")
    s_model = r.get("model")
    s_samar = r.get("samar_category")
    s_price = r.get("best_monthly_price")
    print(f"[{s_score}%] {s_brand} {s_model} (SAMAR: {s_samar}, Price: {s_price})")
