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
            SELECT id, vin, marka, model, wersja, silnik_pojemnosc, silnik_moc, 
                   samar_id, samar_marka, samar_model, samar_klasa, samar_nadwozie_typ, payload 
            FROM oferty_pojazdy 
            WHERE vin LIKE '%WBA11GR%'
        """)
        )
        rows = result.fetchall()

        out = [dict(r._mapping) for r in rows]
        with open("d:/kalk_v3/backend/x3_data.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print("Zapisano dane do x3_data.json. Znaleziono wierszy:", len(out))


asyncio.run(test_db())
