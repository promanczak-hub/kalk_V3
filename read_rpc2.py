import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17@@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")
    
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT pg_get_functiondef(oid) 
            FROM pg_proc 
            WHERE proname = 'rpc_get_alternatives_semantic';
        """))
        for row in result:
            print("----- FUNCTION DEF -----")
            print(row[0])
            print("------------------------")
            
asyncio.run(main())
