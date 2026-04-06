import time
from dotenv import load_dotenv

# Konieczne aby zainicjalizować środowisko z prawidłowymi DB keys
load_dotenv(".env")

from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    print("===========================================")
    print("1. CZYSZCZENIE TABELI vehicle_matrix_cache")
    print("===========================================")

    total_deleted = 0
    while True:
        try:
            # PostgREST zwraca maksymalnie 1000 rekordów. Pętla pozwoli usunąć wszystkie kaskadowo.
            res = (
                supabase.table("vehicle_matrix_cache")
                .delete()
                .gte("duration_months", 0)
                .execute()
            )
            if not res.data or len(res.data) == 0:
                break

            count = len(res.data)
            total_deleted += count
            print(f"Usunięto {count} wierszy...")
        except Exception as e:
            print(f"Błąd podczas czyszczenia cache: {e}")
            break

    print(
        f"-> Zakończono czyszczenie. Łącznie usunięto: {total_deleted} komórek matrycy.\n"
    )

    print("===========================================")
    print("2. POBIERANIE POJAZDÓW Z vehicle_synthesis ")
    print("===========================================")
    try:
        res = supabase.table("vehicle_synthesis").select("id").execute()
        vehicles = res.data or []
        all_ids = [v["id"] for v in vehicles]
        print(
            f"Znaleziono {len(all_ids)} pojazdów przeznaczonych do ponownego przeliczenia z JSONów."
        )
    except Exception as e:
        print(f"Błąd podczas pobierania pojazdów: {e}")
        return

    print("\n===========================================")
    print("3. GENEROWANIE NOWYCH KALKULACJI W CELERY  ")
    print("===========================================")

    # Procesujemy w małych paczkach żeby nie zarżnąć na start połączeń z PostgreSQL
    batch_size = 20
    for i in range(0, len(all_ids), batch_size):
        chunk = all_ids[i : i + batch_size]
        print(
            f"-> Podawanie do Workera Celery paczki zadań: {i + 1} do {min(i + batch_size, len(all_ids))} ..."
        )

        try:
            # Generuje kalkulację i wypycha task jako process_kalkulacja_matrix_task.delay(new_kalk_id)
            refresh_matrix_cache_for_vehicles(chunk)
        except Exception as e:
            print(f"Błąd podczas wypychania paczki: {e}")

        # Małe opóźnienie by RabbitMQ / Redis gładko przełknęły wiadomości
        time.sleep(1)

    print(
        "\n[ZAKOŃCZONO SUKCESEM] Wszystkie logiki wyliczeniowe dla aut zostały wrzucone w tło."
    )
    print(
        "Sprawdź konsolę Celery (tam gdzie odpalone jest run_dev.py lub worker), by obserwować postępy generowania matryc!"
    )


if __name__ == "__main__":
    main()
