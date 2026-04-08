import asyncio
import sys
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase


async def inspect():
    # Use a dummy query to get one row and see keys
    res = supabase.table("vehicle_matrix_cache").select("*").limit(1).execute()
    if res.data:
        print(list(res.data[0].keys()))


if __name__ == "__main__":
    asyncio.run(inspect())
