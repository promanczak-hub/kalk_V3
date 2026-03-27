import asyncio
from core.database import supabase


async def test_delete():
    try:
        res = (
            supabase.table("vehicle_synthesis")
            .delete()
            .eq("id", "00000000-0000-0000-0000-000000000000")
            .execute()
        )
        print(res.data)
    except Exception as e:
        print("EXCEPTION:", repr(e))


if __name__ == "__main__":
    asyncio.run(test_delete())
