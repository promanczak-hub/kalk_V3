import requests
import json

url = "http://localhost:8000/api/calculate-matrix"

payload = {
    "calculation_id": "7a99e7e9-6d6c-4c8b-b2b1-4aaf236cd6bb",
    "vehicle_id": "52997b93-b3ba-4384-b82e-e189bb1720d4",
    "base_price_net": 119268.29,
    "discount_pct": 27.0,
    "factory_options": [
        {
            "name": "Pakiet Assisted Drive (PAB)",
            "price_net": 2195.12,
            "price_gross": 2700,
            "no_discount": False,
            "include_in_wr": False,  # options_in_wr are processed independently inside calculator (usually true if in factory_options, or SAMAR RV checks it natively!) wait, let me set to True as it's included in factory prices!
        },
        {
            "name": "Dywaniki tekstylne (OTD)",
            "price_net": 243.90,
            "price_gross": 300,
            "no_discount": False,
            "include_in_wr": False,
        },
        {
            "name": "Zapasowe koło (PJA)",
            "price_net": 569.11,
            "price_gross": 700,
            "no_discount": False,
            "include_in_wr": False,
        },
    ],
    "service_options": [],
    "samar_category": "Podstawowa - C NIŻSZA ŚREDNIA",
    "engine_name": "Benzyna mHEV (PB-mHEV)",
    "okres_bazowy": 48,
    "przebieg_bazowy": 120000,
    "pricing_margin_pct": 15.0,
    "z_oponami": True,
    "klasa_opony_string": "Medium",
    "odkup_opon_enabled": False,
    "wibor_pct": 3.83,
    "margin_pct": 2.2,
    "initial_deposit_pct": 0.0,
    "replacement_car_enabled": True,
    "include_servicing": True,
    "service_cost_type": "ASO",
    "vehicle_vintage": "current",
    "is_metalic": True,
    "matrix_km_mode": "annual",
    "srednica_felgi": 17,
}

headers = {"Content-Type": "application/json"}

try:
    print("Wywoływanie API kalkulacji...")
    response = requests.post(url, json=payload)
    if not response.ok:
        print(f"Error HTTP {response.status_code}")
        print(response.text)
    else:
        # Pokaż rezultat
        data = response.json()
        print("SUCCESS. Got calculation trace info:")
        with open("d:/kalk_v3/rv_trace.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Saved test to d:/kalk_v3/rv_trace.json")
except Exception as e:
    print("ERROR:")
    print(e)
