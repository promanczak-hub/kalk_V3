import os
import sys

# Ustawienie ścięzki, aby moduł core mógł być zaimportowany
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import supabase
from core.embeddings import generate_embedding

def main():
    query = "bezpieczne i przestronne auto rodzinne na wyjazdy"
    print(f"1. Zapytanie tekstowe: '{query}'\n")
    
    print("2. Generowanie wektora osadzeń (embeddings) za pomocą modelu Gemini...")
    vector = generate_embedding(query)
    
    if not vector:
        print("Nie udało się wygenerować wektora.")
        return
        
    print(f"   Pomyślnie wygenerowano wektor - wymiar: {len(vector)} (fragment: {vector[:3]}...)\n")

    vector_str = f"[{','.join(str(v) for v in vector)}]"
    
    print("3. Przeszukiwanie bazy danych (Hybrid Search: semantyka wg wektora osadzeń)...")
    import httpx
    response = httpx.post(
        f"{supabase.supabase_url}/rest/v1/rpc/rpc_reverse_search",
        headers={
            "apikey": supabase.supabase_key,
            "Authorization": f"Bearer {supabase.supabase_key}",
            "Accept-Profile": "reverse_search",
            "Content-Profile": "reverse_search",
        },
        json={
            "p_semantic_query_vector": vector_str,
            "p_requirements": [],
            "p_search_query": query
        },
        timeout=30.0,
    )
    
    if response.status_code != 200:
        print(f"RPC Error ({response.status_code}): {response.text}")
        return
        
    data = response.json()
    print(f"   Liczba znalezionych dopasowań: {len(data)}\n")
    
    print("4. TOP 5 Wyników wyszukiwania semantycznego:")
    for i, row in enumerate(data[:5]):
        print(f"   [{i+1}] {row.get('brand')} {row.get('model')}")
        print(f"       Trafność (Match Score): {row.get('match_score_pct')}%")
        print(f"       Opłata max: ~{row.get('best_monthly_price')} PLN (ID: {row.get('vehicle_id')})")
        print()

if __name__ == "__main__":
    main()
