import asyncio
from core.database import supabase


async def run():
    # Pick one vehicle ID that exists
    res = supabase.table("vehicle_synthesis").select("id").limit(1).execute()
    if not res.data:
        print("No vehicles found.")
        return

    v_id = res.data[0]["id"]
    print(f"Trying to delete vehicle id: {v_id}")
    try:
        del_res = supabase.table("vehicle_synthesis").delete().eq("id", v_id).execute()
        print("Delete Response:", del_res)
    except Exception as e:
        print("Exception during delete:", repr(e))


asyncio.run(run())
