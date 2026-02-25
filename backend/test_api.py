import httpx
import asyncio


async def test_api():
    url = "http://127.0.0.1:8000/api/calculate-matrix"
    payload = {
        "vehicle_id": "test_octavia_1",
        "base_price_net": 100000.0,
        "discount_pct": 10.0,
        "factory_options": [
            {
                "name": "Lakier",
                "price_net": 2500.0,
                "price_gross": 3075.0,
                "no_discount": False,
            }
        ],
        "service_options": [],
        "grid": {"months": [24, 36], "km_per_year": [10000, 20000]},
        "pricing_margin_pct": 15.0,
        "settings": {},
        "all_season_tires": True,
        "tire_buyback": True,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print("Status", response.status_code)
        print("Response", response.json())


if __name__ == "__main__":
    asyncio.run(test_api())
