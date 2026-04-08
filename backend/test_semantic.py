import asyncio
import os
import sys

# Dodajemy backend do sys.path by widział 'core'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import supabase
from core.embeddings import generate_embedding


async def main():
    print("Generating query vector...")
    query = "Dostawczak z napędem 4x4 do lasu"
    emb = generate_embedding(query)

    if not emb:
        print("Embedding failed!")
        return

    print(f"Generated vector length: {len(emb)}")

    print("Calling 'rpc_search_vehicles_by_text'...")
    vector_str = "[" + ",".join(map(str, emb)) + "]"

    try:
        response = supabase.rpc(
            "rpc_search_vehicles_by_text",
            {"p_query_embedding": vector_str, "p_limit": 5},
        ).execute()

        results = response.data
        if not results:
            print("No matching vehicles found.")
        else:
            print(f"Found {len(results)} matches!")
            for r in results:
                print(
                    f"- {r['brand']} {r['model']} (Score: {r['similarity_score_pct']}%)"
                )

    except Exception as e:
        print(f"Error querying DB: {e}")


if __name__ == "__main__":
    asyncio.run(main())
