import os
import requests
from dotenv import load_dotenv

load_dotenv("d:/kalk_v3/backend/.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def test_key(k, label):
    if not k:
        print(f"{label}: Missing")
        return

    headers = {"apikey": k, "Authorization": f"Bearer {k}"}
    # Try a simple select to a public table or any table
    endpoint = f"{url}/rest/v1/samar_classes?limit=1"
    try:
        resp = requests.get(endpoint, headers=headers)
        print(f"{label} (starts with {k[:10]}...): Status {resp.status_code}")
        if resp.status_code != 200:
            print(f"  Response: {resp.text}")
    except Exception as e:
        print(f"{label} Error: {e}")


print(f"Testing connectivity to {url}")
test_key(key, "SUPABASE_KEY")
test_key(service_key, "SUPABASE_SERVICE_ROLE_KEY")
