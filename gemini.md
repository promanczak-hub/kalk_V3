# Wytyczne AI (Gemini / Claude / Cursor) dla projektu Kalkulator (V3)

Ten projekt ma być w pełni produkcyjny, elastyczny i skalowalny. Oferta kalkulatora będzie stale poszerzana o nowe marki i klasy pojazdów. W związku z tym, podczas pracy nad kodem, bezwzględnie stosuj się do poniższych zasad.

## 1. ZERO HARDKODOWANIA (Konfiguracja zamiast "sztywnych" reguł)

Podczas pisania logiki decyzyjnej **NIGDY** nie wpisuj do instrukcji warunkowych (np. `if`, `match`) konkretnych nazw marek (`BMW`, `Audi`), modeli ani klas pojazdów. W przyszłości baza pojazdów będzie ogromna.

**Jak to rozwiązywać:**

- **Słowniki / Słowniki konfiguracyjne:** Mnożniki, wagi lub specyficzne zasady wyciągaj z mapowań konfiguracyjnych zdefiniowanych jako zmienne środowiskowe, stałe globalne (w wyznaczonym pliku konfiguracyjnym) lub parametry w bazie.

  ```python
  # ZŁE:
  if vehicle.brand == "Porsche":
      residual_value *= 1.15

  # DOBRE:
  premium_multiplier = config.BRAND_MULTIPLIERS.get(vehicle.brand, 1.0)
  residual_value *= premium_multiplier
  ```

- **Baza danych jako źródło prawdy:** Reguły biznesowe oparte na klasie lub marce zawsze powinny być powiązane z danymi w lokalnej bazie Supabase, skąd aplikacja je pobierze.

## 2. "PANCERNE" FUNKCJE (Odporność na błędy)

System nigdy nie powinien się wywalić (Crash 500) z powodu literówki w nazwie marki, pustego ciągu znaków, czy nowej niespodziewanej wartości. Każda funkcja biznesowa czy parser danych z LLM musi być "bulletproof" (pancerny).

**Zasady tworzenia pancernych funkcji:**

- **Ścisłe Typowanie (Strict Typing):** Zawsze używaj pełnego typowania (np. `str | None`, `dict[str, Any]`). Korzystaj z modeli Pydantic do walidacji danych.
- **Domyślne Wartości (Fallbacks) i Miękkie Lądowanie:** Jeśli funkcja napotyka nieznaną markę (np. chiński odpowiednik nowej marki rzadko spotykanej), nie rzucaj nagim wyjątkiem `KeyError`. Przechwyć sytuację, użyj bezpiecznej wartości domyślnej (np. kategorii "STANDARD_UNKNOWN") dla której zadziałają algorytmy, i obowiązkowo zaloguj błąd (`logger.warning`).
- **Obsługa Krawędziowych Zdarzeń (Edge Cases):**
  - Co jeśli puste pole to `None` lub string `"None"`?
  - Co jeżeli nazwa zawiera dodatkowe spacje lub błędną wielkość liter (`" porsche "` zamiast `"Porsche"`)?
  - Przewiduj, że API czasowo zniknie, a zapytanie bazodanowe zwróci pusty stan. Zawsze używaj spójnych metod normalizacji łańcuchów znaków (np. `.strip().upper()`).

## 3. FUZZY MATCHING / NORMALIZACJA WPROWADZANYCH ŚMIECOWYCH DANYCH

Pamiętaj, że dane trafiające do systemu na etapie przetwarzania cenników, konfiguracji lub wyciągania przez LLM, bywają błędne (np. "Wolkswagen", "Vw", "Mercedes Benz" zamiast "Mercedes-Benz").
Zanim nazwa użyta zostanie do zapytań systemowych, upewnij się, że przechodzi przez moduł normalizujący (stripowanie znaków, dopasowanie rozmyte, tablice aliasów).

## 4. TESTOWANIE W ZOPTYMALIZOWANYCH WARUNKACH

Dodając nowy plik konfiguracyjny z mnożnikami, od razu pisz test w `pytest`:

- Test dla popularnej marki (np. "Toyota").
- Test dla marki premium (np. "Porsche").
- **Najważniejsze:** Test dla marki/klasy **całkowicie zmyślonej i nieistniejącej w naszych konfiguracjach** (np. "MarkaX"). Twoja logika w tej sytuacji musi "przeżyć" bez zgłaszania Internal Server Error, aplikując wartość bazową.
