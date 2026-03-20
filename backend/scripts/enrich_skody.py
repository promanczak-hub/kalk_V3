import sys
import os
import time

# Dodaj główny katalog backendu do PYTHONPATH, aby importy działały poprawnie
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase
from core.feature_cross_reference import wipe_vehicle_features
from tasks.enrichment_tasks import enrich_vehicle_features_from_catalog
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    print("Szukam pojazdów Skoda Octavia w bazie danych...")

    # Pobierz wszystkie auta, żeby wyeliminować problem ilike po stronie JSONa
    resp = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    vehicles = resp.data or []

    octavias = []
    for v in vehicles:
        synth = v.get("synthesis_data") or {}
        card = synth.get("card_summary") or {}
        brand = str(card.get("brand") or synth.get("brand") or "").lower()
        model = str(card.get("model") or synth.get("model") or "").lower()

        # Oczyszczenie nazwy marki, żeby obsłużyć np "Škoda"
        brand_clean = brand.replace("š", "s")

        if "skoda" in brand_clean and "octavia" in model:
            octavias.append(v["id"])

    total = len(octavias)
    print(f"Znaleziono {total} aut marki Skoda Octavia.")

    if total == 0:
        return

    print("Rozpoczynam proces twardego resetu i ponownego łączenia z cennikiem...")

    for i, vid in enumerate(octavias, 1):
        print(f"[{i}/{total}] Przetwarzanie auta {vid}...")
        try:
            # Krok 1: Wyczyść obecne cechy i usun stary cache Redis
            wipe_vehicle_features(vid)

            # Krok 2: Uruchom wzbogacanie wg nowej logiki ukarania (Deep Match)
            result = enrich_vehicle_features_from_catalog(vid)

            # Krok 3: Wywołaj przeliczenie macierzy, zeby uaktualnić frontend
            refresh_matrix_cache_for_vehicles([vid])

            print(
                f"  OK: Status {result.get('status')}. Wariant domyślny: {result.get('matched_variant', 'Brak lub Fallback')}"
            )

        except Exception as e:
            print(f"  BŁĄD przy przetwarzaniu {vid}: {e}")

        # Niewielki delay by nie przekroczyć narzutów LLM na sekundę API.
        time.sleep(2)

    print("\nZakończono.")


if __name__ == "__main__":
    main()
