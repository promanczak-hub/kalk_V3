import asyncio
import httpx

payload = {
    "calculation_id": "test",
    "vehicle_id": "44d2cae6-7b6f-45d9-90e2-2532546eee5e",
    "base_price_net": 149975.0,
    "discount_pct": 26.7,
    "factory_options": [],
    "service_options": [],
    "okres_bazowy": 48,
    "przebieg_bazowy": 80000,
    "wibor_pct": 5.85,
    "margin_pct": 2.0,
    "depreciation_pct": None,
    "initial_deposit_pct": 0,
    "replacement_car_enabled": True,
    "add_gsm_subscription": True,
    "add_hook_installation": True,
    "z_oponami": True,
    "klasa_opony_string": "Medium",
    "srednica_felgi": 16,
    "liczba_kompletow_opon": None,
    "korekta_kosztu_opon": True,
    "koszt_opon_korekta": 0,
    "service_cost_type": "ASO",
    "vehicle_vintage": "current",
    "is_metalic": False,
    "pricing_margin_pct": 15.0,
    "manual_wr_correction": 0,
    "pakiet_serwisowy": 0,
    "inne_koszty_serwisowania_netto": 0,
    "settings": {"settings_version_id": None, "overrides": None},
}


async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8000/api/calculate-matrix", json=payload
        )
        data = resp.json()

        for cell in data.get("cells", []):
            if cell["months"] == 48:
                print(
                    f"48m / {cell['km_per_year']} km/yr -> price: {cell['price_net']}"
                )


asyncio.run(main())
