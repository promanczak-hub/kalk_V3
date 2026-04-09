import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17@@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")
    
    # 1. Fetch function definition
    val = await conn.fetchval("""
        SELECT pg_get_functiondef(oid) 
        FROM pg_proc 
        WHERE proname = 'rpc_get_alternatives_semantic';
    """)
    print("----- FUNCTION DEF -----")
    print(val)
    print("------------------------")
    await conn.close()

asyncio.run(main())
