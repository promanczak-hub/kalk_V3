import os
import sys

# Dodajemy backend do sys.path, aby widział moduły z 'core'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tasks.enrichment_tasks import backfill_vehicle_embeddings

if __name__ == "__main__":
    print("Rozpoczynam ręczne generowanie osieroconych wektorów (synchronicznie)...")
    try:
        result = backfill_vehicle_embeddings()
        print(
            f"Zakończono! Zaktualizowano pomyślnie {result.get('successful')}/{result.get('processed')} aut."
        )
    except Exception as e:
        print(f"Błąd krytyczny: {e}")
