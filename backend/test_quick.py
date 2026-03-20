import json
import urllib.request
import urllib.error

payload = {
    "calculation_id": "test",
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
    "settings": {"settings_version_id": None, "overrides": None},
}

req = urllib.request.Request(
    "http://localhost:8000/api/calculate-matrix",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        cells = data.get("cells", [])
        print(f"HTTP {resp.status} | Cells: {len(cells)}")
        if cells:
            print("First cell keys:", list(cells[0].keys())[:12])
            c = cells[0]
            print(
                f"  Okres={c.get('Okres')} Przebieg={c.get('Przebieg')} LacznaStawka={c.get('LacznaStawka')}"
            )
            # Check for old V3 keys
            if "months" in c:
                print("  WARNING: Old V3 key 'months' found!")
            if "price_net" in c:
                print("  WARNING: Old V3 key 'price_net' found!")
        else:
            print("Detail:", data.get("detail", data.get("message", "?")))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:2000]}")
except Exception as e:
    print(f"Error: {e}")
