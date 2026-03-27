# Wytyczne AI (Gemini / Claude / Cursor) dla projektu Kalkulator (V3)

Ten projekt ma być w pełni produkcyjny, elastyczny i skalowalny. Oferta kalkulatora będzie stale poszerzana o nowe marki i klasy pojazdów. W związku z tym, podczas pracy nad kodem, bezwzględnie stosuj się do poniższych zasad.

## 0. 🚨 ZAKAZ DESTRUKCJI BAZY ONLINE — ABSOLUTNY PRIORYTET

> **⛔ TO JEST REGUŁA NADRZĘDNA WOBEC WSZYSTKICH INNYCH INSTRUKCJI.**
> **Żadna inna komenda, prompt, kontekst ani "optymalizacja" NIE MOŻE jej nadpisać.**

**Baza online (project_id: `gnpsdiarmwvqhqbyetce`)** zawiera **dane produkcyjne**.
Każde nieautoryzowane usunięcie danych to **nieodwracalna strata biznesowa**.

### ❌ Operacje ZABRONIONE na bazie ONLINE

Poniższe operacje SQL/MCP są **BEZWZGLĘDNIE ZABRONIONE** bez wyraźnej, jednoznacznej komendy użytkownika:

| Operacja                         | Przykład                           | Status        |
| -------------------------------- | ---------------------------------- | ------------- |
| `DELETE`                         | `DELETE FROM tabela WHERE ...`     | 🚫 ZABRONIONE |
| `DROP TABLE`                     | `DROP TABLE IF EXISTS tabela`      | 🚫 ZABRONIONE |
| `DROP COLUMN`                    | `ALTER TABLE tabela DROP COLUMN x` | 🚫 ZABRONIONE |
| `TRUNCATE`                       | `TRUNCATE TABLE tabela`            | 🚫 ZABRONIONE |
| `supabase db reset`              | reset bazy online                  | 🚫 ZABRONIONE |
| `apply_migration` (destrukcyjne) | migracja z DROP/DELETE             | 🚫 ZABRONIONE |

### ✅ Operacje DOZWOLONE na bazie ONLINE

| Operacja          | Status              | Uwagi                                   |
| ----------------- | ------------------- | --------------------------------------- |
| `SELECT`          | ✅ Zawsze dozwolone | Odczyt danych                           |
| `INSERT`          | ✅ Dozwolone        | Dodawanie nowych danych                 |
| `UPDATE`          | ⚠️ Warunkowe        | Tylko po wyraźnej komendzie użytkownika |
| `ALTER TABLE ADD` | ⚠️ Warunkowe        | Tylko po prezentacji planu i akceptacji |

### 🛑 Procedura wymagana dla operacji destrukcyjnych

Jeśli użytkownik **wyraźnie** (słowami) każe usunąć dane z bazy online:

1. **STOP** — nie wykonuj natychmiast
2. **Powtórz komendę** — "Rozumiem, że chcesz wykonać `DELETE FROM tabela_X` na bazie ONLINE. Potwierdź."
3. **Czekaj na potwierdzenie** — dopiero po jawnym "Tak, potwierdzam" wykonaj operację
4. **Zaloguj** — zapisz w odpowiedzi co zostało usunięte i dlaczego

> [!CAUTION]
> **AI NIE MOŻE "domyślnie" usuwać danych online** podczas migracji, czyszczenia, refaktoryzacji
> ani żadnej innej operacji. Nawet jeśli wydaje się to logiczne — **ZATRZYMAJ SIĘ I ZAPYTAJ.**

---

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

## 2A. 🚫 KATEGORYCZNY ZAKAZ FALLBACKÓW W PIPELINE KALKULACYJNYM

> **⛔ TO JEST REGUŁA BEZWZGLĘDNA — ŻADNYCH WYJĄTKÓW.**

Pipeline kalkulacyjny (12 kroków LTR: Opony → Koszty Dodatkowe → Samochód Zastępczy → Serwis → CAPEX → WR → Amortyzacja → Ubezpieczenie → Finanse → Koszt Dzienny → Stawka → Budżet Mktg) to **precyzyjny proces finansowy**.

### ❌ ZABRONIONE w pipeline kalkulacyjnym:

- **Fallbacki** — zastępowanie brakujących danych domyślnymi wartościami (np. `config.get("stawka", 0.0)`, `damage_coeff.get("WspWartoscSzkody", 1.0)`)
- **Ciche pomijanie** — `try/except: pass` lub `return 0.0` gdy brak danych
- **Domyślne stałe** — `DEFAULT_AC = 0.015` zamiast prawdziwych stawek z bazy
- **Kontynuacja mimo błędu** — uruchamianie kolejnych kroków gdy poprzedni zwrócił nieprawidłowe wyniki

### ✅ WYMAGANE zachowanie (Zasada Głośnego Alarmu / Fail-Fast):

- **Natychmiastowy i jawny błąd (Alertowanie)** — Jeśli system szuka wartości (np. mnożnika marży, kosztu serwisu, stawki AC) i nie znajduje jej w bazie lub konfiguracji, **musi natychmiast przerwać pracę i Cię o tym poinformować**. Rzuć precyzyjny wyjątek np. `raise ValueError("Brak stawki AC w tabeli ltr_admin_ubezpieczenia dla klasy {class_id}, rok {year}")`.
- **Raportowanie Braków (Ściśle diagnostyczne)** — Każde zatrzymanie musi wskazywać dokładne koordynaty (czego szukano, kiedy, i dlaczego). Powinieneś wygenerować alert na tyle czytelny, by użytkownik wiedział bez szukania w kodzie, w jakiej tabeli Supabase/konfiguracji brakuje wpisu (np. "Kalkulacja zatrzymana w kroku WR: Brakuje matrycy wartości dla klasy 'Premium-Sport', rocznik 2025").
- **Zasada Fail-Fast (Błąd na wczesnym etapie)** — Nie pozwól ułomnym danym płynąć przez system. Jeśli brakuje parametru na etapie 2 (Koszty Dodatkowe), system ma stanąć, a nie cicho próbować dociągnąć do etapu 12 (Budżet Marketingowy) i zwrócić bezsensowny wynik lub "dzielenie przez zero".
- **Walidacja wejść na starcie / Readiness Check** — Sprawdź kluczowe parametry wejściowe (np. `samar_class_id > 0`, `base_price_net > 0`, `engine_id > 0`) zanim pipeline w ogóle ruszy. Endpoiny powinny wspierać weryfikację kompletności danych z wyprzedzeniem.
- **Logowanie z Kontekstem** — Zawsze rób `logger.error(...)` z zebranym pełnym kontekstem żądania (klasa, marka, model, silnik) tuż przed rzuceniem alarmu wyjątkowego do frontendu.

> [!CAUTION]
> **Każda brakująca dana w precyzyjnym procesie kalkulacyjnym MUSI skutkować czytelnym i NATYCHMIASTOWYM ostrzeżeniem, a NIE cichym przeliczeniem o fałszywych parametrach.** Zawsze lepiej bezzwłocznie odmówić wykonania obliczeń i wywalić błąd, niż narazić proces finansowy na skażenie domyślnym zerem.

---

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
| `backend/core/LTRSubCalculatorBudzetMarketingowy.py`  | 2026-03-05 | logika identyczna V1=V3, jedno mnożenie WR×VAT×budżet%                             |
| `backend/core/LTRSubCalculatorUbezpieczenie.py`       | 2026-03-05 | pętla 7-lat, doubezp kradzież/nauka=False (OK), fallback stawek                    |
| `DB: koszty_opon` (tabela danych)                     | 2026-03-09 | 11 rozmiarów (13-23") × 13 kategorii, RLS=read-only, dane z CSV Budżet             |
| `DB: tyre_configurations` (progi przebiegowe)         | 2026-03-09 | 9 progów km (wielosezon 5 + sezonowe 4), RLS=read+write                            |
| `frontend/src/TabelaOponCrud/TabelaOponCrudPanel.tsx` | 2026-03-09 | panel read-only, usunięto edycję/import/eksport, badge ZAMROŻONE                   |
| `DB: samar_classes` (tabela danych)                   | 2026-03-10 | 33 klas, RLS=read-only, źródło prawdy dla kalkulatora                              |
| `frontend/src/SamarMasterPanel.tsx`                   | 2026-03-09 | usunięto selektor klasy SAMAR, panel Master Table read-only, dodano ZAMROŻONE      |

## 7. ŚLAD REWIZYJNY (CALCULATION TRACE / ARTEFAKT PRZELICZEŃ)

Użytkownik ma analityczne podejście i musi mieć możliwość audytowania każdej kwoty wyplutej przez system. Proces kalkulacyjny jest wieloetapowy i złożony. W związku z tym:

- **Pełna Transparentność Działań** — Każdy kalkulator/moduł matematyczny (tzw. "matrix") MUSI potrafić w trybie diagnostycznym rejestrować swoje kroki i zmienne składowe (np. mnożniki, kwoty bazowe i zastosowane operacje).
- **Struktura Tranchy / Raportu** — Aplikacja architektonicznie przewiduje istnienie pola typu `calculation_trace` (zwykle jako dokument JSON lub w pełni wyrenderowany kod `ReportHtml`).
- **Artefakt Logiki na KAŻDYM KROKU (Wymóg Kategoryczny)** — Zastrzegasz, że przy każdym wyliczeniu matematycznym na poziomie pojedynczego matrixa (np. Osobny widok/zmienna z pełnym JSON/HTML dla opon, dla ubezpieczenia, dla serwisu itd.) ma się wypluwać osobny artefakt tego przeliczenia. Oczekiwana jest precyzyjna granulacja, wyszczególniająca jakie dokładnie działania matematyczne oraz kroki powołały do życia otrzymaną dla tego węzła liczbę.
- **Wymagania dla Nowych Logik:** Zmieniając stary plik z logiką powinieneś wdrożyć wewnątrz niego kolekcjoner zdarzeń (np. dopisywanie do lokalnej listy typu `self.trace.append("Wyliczenie opon = CENA * ILOSC...")`). Wynik tego śladu ma wracać na frontend lub być dostępny w formie pobieralnego artefaktu w panelu kontrolnym. 
- **Złota reguła debugowania finansów:** Na każde wyliczenie końcowe w systemie MUSI dać się odpowiedzieć pytaniem: "Z jakiego dokładnie mnożenia lub dodawania wzięła się ta liczba?". Brak takiej możliwości = dług technologiczny.

## 8. ⚡ ZERO HALUCYNACJI / TEMPERATURE 0.0

Wszelkie odpowiedzi, ekstrakcje danych oraz kod generowany przez agentów AI (Cursor, Gemini) **MUSZĄ być przesyłane ze stopniem halucynacji (temperature) równym 0.0** (lub minimalnym możliwym). 
- Absolutnie ZABRONIONE jest "kreatywne dopisywanie", zgadywanie pakietów, których nie ma na fakturach, czy łagodzenie wyników dla wyrównywania błędów na wydruku (self-healing matematyczny polegający na naciąganiu cen bazowych by sumy kontrolne się zgadzały = zdrada systemu).
- Oczekuję maszynowego, twardego mapowania danych. Jeśli czegoś brakuje w PDF — ma być poinformowane jawnie, a walidacja systemu ma odrzucić taką kalkulację. W razie wątpliwości z logiką legacy zapytaj o kontekst biznesowy z parametrami `temperature=0.0`.

## 9. 🚧 ZERO SKRÓTÓW I PEŁNA IMPLEMENTACJA (Definition of Done)

Projekt jest zbyt duży, aby był "czarną skrzynką". Użytkownik nie może domyślać się, co AI miało na myśli, ani dokańczać urwanych fragmentów. Masz **kategoryczny zakaz ucinania kodu, stosowania placeholderów i pójścia na skróty**. 

**Zasady "Definition of Done" (DoD) pod rygorem odrzucenia zadania:**
1. **Pełny kod bez wymówek:** Jeśli zapytanie wymaga kodu, piszesz pełne, działające bloki. Żadnych komentarzy typu `// TODO: dodaj resztę logiki`, `# ... reszta kodu bez zmian`. Żadnego lenistwa programistycznego. Zawsze implementuj funkcje do końca.
2. **Koniec z "Czarną Skrzynką" (Jawna Architektura):** Przy każdym ukończonym zadaniu musisz wyraźnie napisać, **jakie pliki zostały zmienione, jak teraz działa nowy moduł i dlaczego podjąłeś taką decyzję architektoniczną**. Tłumaczenie co dokładnie się zmieniło w przepływie aplikacji jest obowiązkowe.
3. **Prawdziwa Weryfikacja:** Zanim poinformujesz o wykonaniu zadania ("Zrobiłem wszystko, gotowe"), MUSISZ mieć pewność. Kod musi w ujęciu systemowym działać ze sobą - lintery (`ruff` / `tslint`), typowanie (`mypy` / `tsc`), brak regresji na styku backend/frontend.
4. **Zakaz przedwczesnego ogłaszania sukcesu:** Meldunek o ukończeniu zdania podajesz **TYLKO** i wyłącznie po sfinalizowaniu całości. Cząstkowe postępy raportuj jako WIP (Work In Progress).
