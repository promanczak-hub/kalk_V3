import asyncio
import json
import httpx

async def run():
    vid = 'ff6790e3-5e3e-4bd8-a490-0156affd11ca'
    payload = {
        "vehicle_ids": [vid],
        "duration_months": 60,
        "annual_mileage": 20000,
        "margin": 2.0
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post('http://127.0.0.1:8000/api/scoring-search/cache/batch-prices', json=payload)
        print(resp.status_code)
        print(json.dumps(resp.json(), indent=2))

if __name__ == '__main__':
    asyncio.run(run())
