import asyncio
import httpx


async def find_match():
    target_base = 4682.45
    target_rate = 5382.13

    # Base price was parsed as 222800.
    # Total price was 272563.
    # Real base netto is 222800 / 1.23 = 181138.
    # Real total netto is 272563 / 1.23 = 221595.

    test_prices = [
        222800,
        272563,
        222800 / 1.23,
        272563 / 1.23,
        198970.99,
        198970.99 / 1.23,
        181138.21,
        161765.03,
    ]

    wibors = [4.82, 5.0, 5.85]
    margins = [10.0, 13.0, 15.0]
    discounts = [0, 27]
    tires = ["Premium", "Medium", "Budget"]

    async with httpx.AsyncClient() as c:
        for p in test_prices:
            for w in wibors:
                for m in margins:
                    for d in discounts:
                        for t in tires:
                            payload = {
                                "okres_miesiecy": [36],
                                "przebieg_roczny": [60000],
                                "base_price_net": p,
                                "discount_pct": d,
                                "factory_options": [],
                                "service_options": [],
                                "wibor_pct": w,
                                "margin_pct": 2.0,
                                "pricing_margin_pct": m,
                                "srednica_felgi": 19,
                                "profil_opony": 40,
                                "klasa_opony_string": t,
                                "vehicle_id": "c81aac34-abeb-4dc7-884a-6c26488c099b",
                                "stan_json": {
                                    "vehicle_id": "c81aac34-abeb-4dc7-884a-6c26488c099b",
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
                        r = await c.post(
                            "http://localhost:8001/api/calculate-matrix", json=payload
                        )
                        data = r.json()
                        cells = data.get("cells", [])

                        target = [
                            x
                            for x in cells
                            if x["months"] == 36 and x["km_per_year"] == 60000
                        ]
                        if target:
                            cell = target[0]
                            diff_base = abs(cell["base_cost_net"] - target_base)
                            diff_rate = abs(cell["price_net"] - target_rate)
                            if diff_base < 10 or diff_rate < 10:
                                print(
                                    f"MATCH! Price: {p}, Wibor: {w}, Margin: {m}, Discount: {d} -> Rate: {cell['price_net']}, Base: {cell['base_cost_net']}"
                                )


if __name__ == "__main__":
    asyncio.run(find_match())
