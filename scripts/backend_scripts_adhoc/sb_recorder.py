from seleniumbase import SB
import time


def run_sb_recorder():
    print("===============")
    print("Uruchamiam przeglądarkę w trybie Undetected ChromeDriver (Stealth)")
    print("===============")

    # Inicjalizujemy przeglądarkę z uc=True (tryb stealth)
    with SB(uc=True, test=True, window_size="1920,1080") as sb:
        # Otwieramy stronę
        url = "https://google.com"
        print(f"Otwieram stronę: {url}")
        sb.driver.uc_open_with_reconnect(url, 4)

        print("\nPrzeglądarka uruchomiona!")
        print("Możesz teraz wykonywać operacje na stronie (symulować działanie).")
        print(
            "W konsoli będą drukowane informacje. Aby zakończyć, naciśnij CTRL+C w terminalu lub po prostu zamknij okno przeglądarki."
        )
        print("===============\n")

        try:
            # Utrzymujemy przeglądarkę otwartą do momentu jej zamknięcia przez użytkownika
            while True:
                time.sleep(1)
                # Prosty check czy przeglądarka nadal działa (jeśli user zamknie okno, to wywali wyjątek)
                _ = sb.driver.title
        except Exception:
            print("Zakończono sesję.")


if __name__ == "__main__":
    try:
        run_sb_recorder()
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika.")
