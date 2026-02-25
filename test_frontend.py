from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Nawigowanie do kalkulatora (frontendu)...")
        page.goto("http://localhost:5175/")

        print("Oczekiwanie na ładowanie modalu Control Center...")
        page.wait_for_selector("text=Control Center", timeout=5000)

        # Click the tab to switch to Control Center
        page.get_by_role("tab", name="CONTROL CENTER (PARAMETRY GLOBALNE)").click()

        # Wait for the Zapisz Ustawienia button
        print("Szukanie przycisku zapisu...")
        zapisz_btn = page.locator("button:has-text('Zapisz ustawienia')")
        zapisz_btn.wait_for(state="visible", timeout=5000)

        print("Klikanie Zapisz Ustawienia...")
        zapisz_btn.click()

        # Check for success message or error message
        try:
            page.wait_for_selector(
                "text=Zapisz ustawienia pomyślnie na serwerze i w bazie docelowej!",
                timeout=5000,
            )
            print(
                "🚀 SUKCES: Otrzymano zielony komunikat o zapisie! Błąd 500 nie wystąpił."
            )
        except Exception:
            print(
                "Nie znaleziono komunikatu sukcesu w ciągu 5 sekund, sprawdzanie czy jest błąd."
            )
            # check for alert error
            alerts = page.locator(".MuiAlert-message")
            if alerts.count() > 0:
                print(f"❌ WYKRYTO BŁĄD UI: {alerts.nth(0).inner_text()}")
            else:
                print(
                    "Cisza, nie ma sukcesu i nie ma powiadomienia o błędzie. Sprawdź logi sieci."
                )

        browser.close()


if __name__ == "__main__":
    run()
