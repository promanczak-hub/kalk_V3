import asyncio
import httpx
import json


async def m():
    payload = {
        "okres_miesiecy": [36],
        "przebieg_roczny": [60000],
        "base_price_net": 222800.0,
        "discount_pct": 27.0,
        "factory_options": [],
        "service_options": [],
        "wibor_pct": 4.82,
        "margin_pct": 2.0,
        "pricing_margin_pct": 13.0,
        "srednica_felgi": 19,
        "profil_opony": 40,
        "klasa_opony_string": "Premium",
        "vehicle_id": "c81aac34-abeb-4dc7-884a-6c26488c099b",
        "samar_class_id": 19,
        "engine_type_id": 1,
        "stan_json": {
            "vehicle_id": "c81aac34-abeb-4dc7-884a-6c26488c099b",
            "samar_class_id": 19,
            "engine_type_id": 1,
            "brand": "CUPRA",
            "model": "LEON SPORTSTOURER",
            "toggles": {
                "gps_required": True,
                "replacement_car": True,
                "hook_installation": True,
                "include_servicing": True,
                "express_pays_insurance": True,
            },
        },
    }

    async with httpx.AsyncClient() as c:
        r = await c.post("http://localhost:8001/api/calculate-matrix", json=payload)
        d = r.json()
        target = [
            x
            for x in d.get("cells", [])
            if x["months"] == 36 and x["km_per_year"] == 60000
        ]
        if target:
            c = target[0]
            print(
                f"Months: {c['months']}, KM: {c['km_per_year']}, RATE: {c['price_net']}, BASE: {c['base_cost_net']}"
            )
            print("FINANCE:")
            print(json.dumps(c["breakdown"]["finance"], indent=2))
            print("TECHNICAL:")
            print(json.dumps(c["breakdown"]["technical"], indent=2))
        else:
            print("ERROR", d)


if __name__ == "__main__":
    asyncio.run(m())
