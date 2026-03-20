import requests

ref = "gnpsdiarmwvqhqbyetce"
token = "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9"

url = f"https://api.supabase.com/v1/projects/{ref}/database/query"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

with open(
    r"d:\kalk_v3\supabase\migrations\20260319102400_update_similar_vehicles_scoring.sql",
    "r",
    encoding="utf-8",
) as f:
    sql = f.read()

# Let's first try a simple SELECT to verify the endpoint is correct
try:
    resp = requests.post(url, headers=headers, json={"query": "SELECT 1;"})
    print("Test status code:", resp.status_code)
    print("Test response:", resp.text)

    if resp.status_code == 200 or resp.status_code == 201:
        print("Test passed. Applying migration...")
        resp2 = requests.post(url, headers=headers, json={"query": sql})
        print("Migration status code:", resp2.status_code)
        print("Migration response:", resp2.text)
    elif resp.status_code == 404:
        print("Endpoint /database/query not found. Trying /pg-commands...")
        url_alt = f"https://api.supabase.com/v1/projects/{ref}/pg-commands"
        resp3 = requests.post(url_alt, headers=headers, json={"query": "SELECT 1;"})
        print("Alt test status:", resp3.status_code)
        print("Alt response:", resp3.text)

except Exception as e:
    print("Error:", e)
