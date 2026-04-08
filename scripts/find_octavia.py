import asyncio
import sys
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase


async def find():
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .ilike("synthesis_data->card_summary->>vehicle_name", "%Octavia%")
        .limit(5)
        .execute()
    )

    if res.data:
        for v in res.data:
            print(
                f"ID: {v['id']} | Name: {v['synthesis_data']['card_summary'].get('vehicle_name')}"
            )
    else:
        print("No Octavia found.")


if __name__ == "__main__":
    asyncio.run(find())
