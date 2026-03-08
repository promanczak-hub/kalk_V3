from DrissionPage import ChromiumPage, ChromiumOptions
import time
import traceback
import sys
import json
import os
from datetime import datetime


def run_dp_recorder():
    print("===============")
    print("Uruchamiam DrissionPage - Tryb SNIFFER (Przechwytywanie API)")
    print("===============")

    # Tworzymy folder na zrzuty jeśli nie istnieje
    os.makedirs("intercepted_data", exist_ok=True)

    co = ChromiumOptions()
    co.set_argument("--start-maximized")

    page = ChromiumPage(co)

    # WŁĄCZENIE NASŁUCHIWANIA SIECI (API INTERCEPTOR)
    # Możemy podać tu część URL-a na którego czekamy, albo regex. Zostawiam puste/odkomentuj żeby złapać wszystko
    # Dla aut i kalkulacji zwykle API w tego typu systemach ma słowa takie jak "api", "calc", "graphql", "vehicles"
    # page.listen.start('api/') # Możesz odkomentować i sprecyzować jeśli znasz URL endpointu
    page.listen.start()  # Łapiemy na razie wszystkie zasoby XHR/Fetch, żeby nie przegapić JSONów

    url = "https://rms.express"  # Zmiana adresu na środowisko RMS z kalkulacjami
    print(f"Otwieram przeglądarkę. Możesz wejść na portal z autami.")
    page.get(url)

    print("\nPrzeglądarka uruchomiona!")
    print("Rob swoje - Wykliwykuj auta. Skrypt w tle łapie każdy request JSON!")
    print(
        "W konsoli będą drukowane informacje. Aby zakończyć, zamknij okno przeglądarki."
    )
    print("===============\n")

    caught_count = 0
    try:
        while True:
            # 1. Czekamy ułamek sekundy (skrypt żyje własnym życiem obok okna usera)
            time.sleep(0.5)

            # 2. Wyłapujemy wszystkie pakiety z bufora
            for packet in page.listen.steps():
                # Sprawdzamy czy mamy obiekt response (może być None przy zablokowanych XHR)
                if not packet.response:
                    continue

                # Pobieramy bezpiecznie i sprawdzamy nagłówki
                headers = packet.response.headers or {}
                content_type = headers.get(
                    "Content-Type", headers.get("content-type", "")
                )

                if content_type.startswith(
                    "application/json"
                ) or packet.resourceType in ["fetch", "xhr"]:
                    url_req = packet.request.url
                    # Odsiewamy śmieci (tracking, analytics itp.)
                    if "google-analytics" in url_req or "sentry" in url_req:
                        continue

                    body = packet.response.body
                    if body:
                        caught_count += 1
                        timestamp = datetime.now().strftime("%H%M%S")
                        safe_url = url_req.split("?")[0].split("/")[
                            -1
                        ]  # sama końcówka endpointu żeby ładnie nazwać plik
                        if not safe_url:
                            safe_url = "root"

                        filename = f"intercepted_data/zapytanie_{caught_count}_{timestamp}_{safe_url[:20]}.json"

                        try:
                            # Próbujemy rozpoznać i zapisać czysty sformatowany JSON
                            parsed_json = (
                                json.loads(body) if isinstance(body, str) else body
                            )
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(parsed_json, f, indent=4, ensure_ascii=False)
                            print(
                                f"[+] Złapano i zapisano JSON: {filename} (URL: {url_req[:80]}...)"
                            )
                        except Exception:
                            # Jeśli to nie czysty JSON, zapisujemy jako text
                            filename = filename.replace(".json", ".txt")
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(str(body))
                            print(
                                f"[*] Złapano odpowiedź (Format Text/Inny): {filename}"
                            )

            # 3. Zabezpieczenie przed błędem - po prostu czekamy
            pass

    except Exception as e:
        print(f"\n[INFO] Wystąpił błąd w pętli głównej:")
        traceback.print_exc()
        # Chcemy by użytkownik nadal miał otwarte okno nawet jak skrypt się wywali
        input("Wciśnij ENTER aby zamknąć przeglądarkę...")

    page.quit()


if __name__ == "__main__":
    try:
        run_dp_recorder()
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika (CTRL+C).")
        sys.exit(0)
