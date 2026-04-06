import asyncio
import json


async def test_db():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text

    db_url = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(
            text("""
            SELECT *
            FROM fleet_management_view 
            WHERE model LIKE '%X3%'
        """)
        )
        rows = result.fetchall()

        out = [dict(r._mapping) for r in rows]
        with open("d:/kalk_v3/backend/local_x3_data.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False, default=str)
        print(f"Zapisano {len(out)} pojazdów do local_x3_data.json.")


asyncio.run(test_db())
