import asyncio
import httpx


async def test_delete():
    async with httpx.AsyncClient() as client:
        # Use a dummy ID to see if we get 500 or 200
        res = await client.post(
            "http://127.0.0.1:8000/api/delete-vehicle",
            json={"vehicle_id": "00000000-0000-0000-0000-000000000000"},
        )
        print("Status:", res.status_code)
        print("Body:", res.text)


asyncio.run(test_delete())
