import requests

url = "https://gnpsdiarmwvqhqbyetce.supabase.co/rest/v1/samar_classes?select=count"
key = "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9"

headers = {"apikey": key, "Authorization": f"Bearer {key}"}

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
