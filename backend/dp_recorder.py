from DrissionPage import ChromiumPage, ChromiumOptions
import time
import sys


def run_dp_recorder():
    print("===============")
    print("Uruchamiam DrissionPage (Chromium w trybie Stealth)")
    print("===============")

    # Konfiguracja opcji Chromium dla maksymalnego 'stealth'
    co = ChromiumOptions()
    co.set_argument("--start-maximized")
    # Opcje anti-bot są włączone domyślnie w DrissionPage
    # co.set_user_agent(...) - DP radzi z tym sobie automatycznie

    page = ChromiumPage(co)

    url = "https://google.com"
    print(f"Otwieram stronę: {url}")
    page.get(url)

    print("\nPrzeglądarka uruchomiona!")
    print(
        "Możesz teraz wykonywać operacje na stronie. DrissionPage omija zabezpieczenia łącząc się po CDP."
    )
    print(
        "W konsoli będą drukowane informacje. Aby zakończyć, zamknij okno przeglądarki."
    )
    print("===============\n")

    try:
        # Kod będzie trzymał proces zapętlony dopóki okno przeglądarki jest otwarte
        while True:
            time.sleep(1)
            # page.title wyrzuci błąd, gdy strona/przeglądarka zostanie zamknięta
            _ = page.title
    except Exception as e:
        print("Zamknięto przeglądarkę, kończę proces.")

    page.quit()


if __name__ == "__main__":
    try:
        run_dp_recorder()
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika (CTRL+C).")
        sys.exit(0)
