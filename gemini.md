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

## 5. ZAKAZ SKRACANIA KLUCZOWYCH PĘTLI MATEMATYCZNYCH (V1 PARITY)

Algorytmy w systemie (np. ubezpieczenie czy symulacja wartości rezydualnej) historycznie wykonywały się przez pełne 7 lat, nawet dla krótszych umów. Ten mechanizm ma zastosowanie biznesowe przy szacowaniu długoterminowych wskaźników i jest **konieczny**.

**Zasady dotyczące pętli na przestrzeni czasu:**

- **NIGDY** nie optymalizuj kodu poprzez przerywanie (`break`) 7-letniej (lub innej, sztywno zdefiniowanej) pętli tylko dlatego, że okres trwania leasingu jest krótszy (np. 4 lata / 48 miesięcy).
- Obliczenia zawsze muszą przejść przez wymaganą liczbę iteracji (np. `self.LICZBA_LAT = 7`).
- Jeśli w bazie dla wyższych lat (np. rok 7) brakuje wpisów w stawkach, **ZASTOSUJ FALLBACK** z ostatniego dostępnego roku lub pierwszego roku bazowego (by zapewnić "miękkie lądowanie" z zachowaniem struktury algorytmu), ale nie wykraczaj poza zdefiniowaną liczbę potrąceń i nie skracaj obliczeń przestrzennych.

## 6. 🔒 ZAMROŻONE MODUŁY (NIE MODYFIKOWAĆ)

Poniższe pliki przeszły pełen audyt V1↔V3 i są zatwierdzone przez użytkownika.
**AI NIE MOŻE modyfikować tych plików bez wyraźnej komendy: "Odmroź moduł X".**

| Plik                                                 | Audyt      | Opis zmian                                                                         |
| ---------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------- |
| `backend/core/LTRSubCalculatorOpony.py`              | 2026-03-05 | ×4 usunięto (DB = cena za komplet), fallbacki → ValueError                         |
| `backend/core/LTRSubCalculatorKosztyDodatkowe.py`    | 2026-03-05 | korekta przygotowania dodana, cost_sales_prep=1040, TODO mock czynszu              |
| `backend/core/LTRSubCalculatorSamochodZastepczy.py`  | 2026-03-05 | logika identyczna V1=V3, stawki potwierdzone                                       |
| `backend/core/samar_rv.py`                           | 2026-03-05 | 6-krokowy algorytm WR, 4-level cascade body correction, 7-lat compound deprecjacja |
| `backend/core/LTRSubCalculatorUtrataWartosciNew.py`  | 2026-03-05 | wrapper SAMAR→LTR, konwersja brutto/netto, resolver class/engine ID                |
| `backend/core/LTRSubCalculatorSerwisNew.py`          | 2026-03-05 | stawka km SAMAR, floor=1667 km/mc (20k/yr), korekta%, power_band                   |
| `backend/core/LTRSubCalculatorCenaZakupu.py`         | 2026-03-05 | netto-based CAPEX, transport+opony+GSM+pakiet, rabat discountable/non-disc         |
| `backend/core/LTRSubCalculatorAmortyzacja.py`        | 2026-03-05 | logika identyczna V1=V3, guard okres≤0                                             |
| `backend/core/LTRSubCalculatorKosztDzienny.py`       | 2026-03-05 | logika identyczna V1=V3, coeff=30.4, wymaga suma_odsetek_bez_czynszu z Finanse     |
| `backend/core/LTRSubCalculatorBudzetMarketingowy.py` | 2026-03-05 | logika identyczna V1=V3, jedno mnożenie WR×VAT×budżet%                             |
| `backend/core/LTRSubCalculatorUbezpieczenie.py`      | 2026-03-05 | pętla 7-lat, doubezp kradzież/nauka=False (OK), fallback stawek                    |
