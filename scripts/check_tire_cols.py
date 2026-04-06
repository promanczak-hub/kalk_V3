import asyncio
import os
import sys
import json
from pathlib import Path

# Fix path to include backend
sys.path.append(str(Path("d:/kalk_v3/backend")))

from core.database import supabase

async def inspect():
    res = supabase.table("koszty_opon").select("*").limit(1).execute()
    if res.data:
        print(json.dumps(res.data[0], indent=2))
    else:
        print("No data in koszty_opon")

if __name__ == "__main__":
    asyncio.run(inspect())
