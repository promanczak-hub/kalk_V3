import asyncio
import httpx
import time

API_URL = "http://localhost:8000/api/scoring-search/cache/batch-similar"

async def fetch_batch(client, i):
    payload = {
        "vehicle_ids": [
            "d824d5ba-e6b3-4f91-a1bf-10bd0b88e14b", 
            "26e81bd1-5af8-4f81-8072-0cbdeef4f647",
            "920fb6c4-b86e-4ccb-b6fb-ea60dbea1ad3",
            "dbdfeb74-7c39-4d33-bc2c-e2f4de37a6b2",
            "fcb455b8-5085-48b8-b2ac-6e2ed8c2eec2"
        ],
        "limit": 5,
        "duration_months": 36,
        "annual_mileage": 15000
    }
    try:
        start_time = time.time()
        response = await client.post(API_URL, json=payload, timeout=30.0)
        elapsed = time.time() - start_time
        return f"Request {i}: Status {response.status_code}, Time: {elapsed:.2f}s"
    except Exception as e:
        return f"Request {i}: Failed with error: {e}"

async def main():
    print("Starting stress test for batch-similar endpoint...")
    async with httpx.AsyncClient() as client:
        # Fire 20 concurrent requests
        tasks = [fetch_batch(client, i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            print(res)

if __name__ == "__main__":
    asyncio.run(main())
