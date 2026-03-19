import urllib.request
import json
import ssl
import sys
import os

# To call wipe_vehicle_features we can just use the DB directly or use the core module.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.feature_cross_reference import wipe_vehicle_features

def main():
    vehicle_id = "4843642e-8dad-4367-bae2-ba772f5f4a3e"
    # Ten cennik ma wypelnione `standard_equipment`
    catalog_id = "716122f6-e164-48eb-a1cd-24c05af75475"
    
    print("Czyszczenie starych dowodów z cennika (katalog)...")
    wipe_vehicle_features(vehicle_id, "catalog")
    
    url = f"http://localhost:8000/api/features/vehicle/{vehicle_id}/cross-reference"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    data = json.dumps({"catalog_ids": [catalog_id]}).encode('utf-8')
    
    print(f"Wywoływanie endpointa: {url}")
    print(f"Dane: {data.decode('utf-8')}")
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        response = urllib.request.urlopen(req, context=ctx)
        resp_body = response.read().decode('utf-8')
        resp_json = json.loads(resp_body)
        print("\n=== SUKCES ===")
        print(json.dumps(resp_json, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print("BŁĄD:", e)

if __name__ == "__main__":
    main()
