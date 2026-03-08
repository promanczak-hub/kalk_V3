import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth
import sys


async def run_stealth_recorder():
    async with async_playwright() as p:
        # Uruchamiamy przeglądarkę w trybie widocznym (headless=False)
        browser = await p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )

        # Tworzymy nowy kontekst z losowym (ale realistycznym) User-Agentem
        # Uruchamiamy nagrywanie wideo w katalogu "videos" i ustawiamy stały rozmiar okna
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            record_video_dir="videos/",
        )

        page = await context.new_page()

        # Aktywacja trybu stealth
        await stealth(page)

        url = "https://google.com"
        print(f"Otwieram stronę główną: {url}")
        await page.goto(url)

        print("===============")
        print("Przeglądarka uruchomiona!")
        print(
            "Wszystko co teraz zrobisz w tym oknie jest NAGRYWANE (wideo w folderze 'videos')."
        )
        print(
            "Kiedy będziesz chciał zakończyć sesję, zamknij okno przeglądarki ręcznie."
        )
        print("===============")

        # Oczekujemy na zdarzenie zamknięcia strony/okna przez użytkownika
        await page.wait_for_event("close", timeout=0)
        await context.close()
        await browser.close()

        print("Sesja zakończona, wideo udostępnione w folderze 'videos'.")


if __name__ == "__main__":
    try:
        asyncio.run(run_stealth_recorder())
    except KeyboardInterrupt:
        print("\nPrzerwano nagrywanie.")
