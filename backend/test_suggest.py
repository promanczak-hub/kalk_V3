import asyncio
import traceback
from api.catalog_routes import suggest_catalogs


async def run():
    try:
        res = await suggest_catalogs("c81aac34-abeb-4dc7-884a-6c26488c099b")
        print(res)
    except Exception as e:
        print("ERROR:")
        traceback.print_exc()


asyncio.run(run())
