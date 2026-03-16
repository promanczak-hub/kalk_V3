import json
import urllib.request
import urllib.error

# Fetch the active calculation
try:
    req = urllib.request.Request("http://localhost:8000/api/kalkulacje")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        calc_id = data[0]['id'] if data else None
except Exception:
    calc_id = "55f462bb-3ae6-4e00-8911-c91795c76747" # default

payload = {
  "calculation_id": calc_id,
  "vehicle_id": "test",
  "base_price_net": 150000,
  "discount_pct": 5,
  "factory_options": [],
  "service_options": [],
  "okres_bazowy": 48,
  "przebieg_bazowy": 80000,
  "wibor_pct": 5.0,
  "margin_pct": 2.0,
  "depreciation_pct": 50,
  "initial_deposit_pct": 0,
  "replacement_car_enabled": True,
  "add_gsm_subscription": True,
  "add_hook_installation": False,
  "z_oponami": True,
  "klasa_opony_string": "Medium",
  "srednica_felgi": 18,
  "liczba_kompletow_opon": None,
  "korekta_kosztu_opon": True,
  "koszt_opon_korekta": 0,
  "service_cost_type": "ASO",
  "vehicle_vintage": "current",
  "is_metalic": True,
  "pricing_margin_pct": 15.0,
  "manual_wr_correction": 0,
  "pakiet_serwisowy": 0,
  "inne_koszty_serwisowania_netto": 0,
  "settings": { "settings_version_id": None, "overrides": None }
}

req2 = urllib.request.Request(
    "http://localhost:8000/api/calculate-matrix",
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req2) as resp:
        result = json.loads(resp.read().decode())
        
        cells = result.get('cells', [])
        print(f"Got {len(cells)} cells.")
        if cells:
            cell = cells[0]
            print("First cell keys:")
            print(", ".join(cell.keys()))
            
            # Check for any None values in standard keys
            for c in cells:
                for k in ["Okres", "Przebieg", "KosztyLaczneMC", "LacznaStawka", "CzynszFinansowy", "Serwis", "Opony", "Ubezpieczenie", "SamochodZastepczy", "Admin", "WR"]:
                    if c.get(k) is None:
                        print(f"NULL VALUE DETECTED for key {k} in cell {c['Okres']}mc / {c['Przebieg']}km")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
