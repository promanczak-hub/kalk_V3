import os
import requests
from supabase import create_client

url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
# The provided key sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9 was truncated in the log
# Let's try the full versions we found
keys = [
    "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9", # From .env
    "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz",     # From seeder/seeders/test files
    "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9"  # From user prompt earlier
]

for key in keys:
    print(f"\n--- Testing key: {key[:15]}... ---")
    
    # 1. Test via requests (Direct Postgrest)
    try:
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/rest/v1/samar_classes?select=count", headers=headers, timeout=5)
        print(f"Direct REST Status: {r.status_code}")
        if r.status_code == 200:
            print(f"SUCCESS (REST): {r.text}")
        else:
            print(f"FAILED (REST): {r.text}")
    except Exception as e:
        print(f"ERROR (REST): {e}")

    # 2. Test via supabase-py
    try:
        sb = create_client(url, key)
        res = sb.table("samar_classes").select("count", count="exact").limit(1).execute()
        print(f"SUCCESS (SDK): Count {res.count}")
    except Exception as e:
        print(f"FAILED (SDK): {e}")
