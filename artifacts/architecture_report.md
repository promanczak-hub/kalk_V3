# Dokumentacja Architektury i Raport Działania: Kalkulator V3 (LTR V2)

Ten dokument to kompleksowy i szczegółowy opis mechaniki działania systemu **Kalkulator V3**, opisujący jego funkcje krok po kroku, architekturę usług, baz danych, endpointy webowe oraz dokładne mapowanie wszystkich wdrożonych widoków (stron). Pozwala on całkowicie wejść w sposób funkcjonowania całego ekosystemu aplikacji stworzonej w oparciu o środowisko AI / RPA dla systemu analityki finansowej i leasingowej.

---

## 1. Przepływ Systemu. Funkcje aplikacji (Krok po kroku)

Aplikacja **Kalkulator V3** służy do profesjonalnej wyceny stawek długoterminowego wynajmu oraz leasingu pojazdów samochodowych dla floty samochodowej. Mechanika i przepływ zdarzeń aplikacji opiera się na **Single Extraction, Multiple Consumption (SEMC)** (pojedyncza zautomatyzowana ekstrakcja danych – wiele ścieżek wykorzystania na warstwach analitycznych):

**KROK 1: Analiza Dokumentu (Ekstrakcja AI)**
- Handlowiec lub Analityk wrzuca plik PDF (ofertę cenową od Dealera lub cenniki katalogowe aut).
- Frontend wysyła to bezpośrednio na Backend (`FastAPI`), który powierza zadanie robotowi odpalonemu jako zadanie w tle połączone kolejką asynchroniczną (`Redis` + `Celery`).
- Sztuczna Inteligencja (`Google GenAI / Vertex`) czyta tekst, odnajdując najważniejsze klamry: pakiety dodatkowe, ubezpieczenie, rok modelowy i tworzy **"Cyfrowego Bliźniaka"** pojazdu w postaci usystematyzowanego strukturalnie obiektu obłożonego rygorem modeli Pydantic. Posiada mechanizm zapobiegający halucynacji AI (Temperature = `0.0`).

**KROK 2: Identyfikacja Pojazdu (Reverse Search / Dopasowanie Słownikowe)**
- Zaimportowane cechy samochodu muszą zgadzać się ze słownikiem `SAMAR`.
- Jeśli wpisane zostały dane zabrudzone typu "Vw Tuareg", system za pomocą logiki `Fuzzy Matching` naprawia parametry, łącząc ofertę pod docelowy silnik i kategorię samochodu, pobierając dedykowane parametry marży operacyjnej i polityki kosztów opon dostępnych dla klasy modelowej pojazdu.

**KROK 3: Uruchomienie Kalkulatora i Narzutów Operacyjnych (12-stopniowy pipeline LTR_Kalkulator)**
Aplikacja, opierając się na architekturze z 12 niezależnych pod-kalkulatorów ("Sub-Calculators"), odnajduje matematyczną wartość rat w funkcji czasu:
1. **Opony**
2. **Koszty Dodatkowe**
3. **Samochód Zastępczy**
4. **Serwis** 
5. **Cena Zakupu (CAPEX)** — w tym nałożenie korekt administracyjnych (kolor, nadwozie/zabudowa).
6. **Utrata Wartości (Wartość Rezydualna / WR)**
7. **Amortyzacja** 
8. **Ubezpieczenie** (z podtrzymywaniem na kradzież i uwzględnieniem "Współczynnika Szkody").
9. **Finanse (Rata PMT)**
10. **Koszt Dzienny** 
11. **Stawka Ostateczna** 
12. **Budżet Marketingowy**

*UWAGA! W całym procesie stosowana jest polityka **Zero Fallbacks** pod rygorem **Fail-Fast** — jeżeli algorytm w kroku trzecim wykryje anomalię, wypluwa wyjątek i przerywa kalkulację bez podstawiania fałszywych wartości.* Następnie dla całości operacji gromadzony jest raport "Złotej Reguły" znany w aplikacji jako "Ślad Audytowy/Calculation Trace".

**KROK 4: Cache’owanie Ciężkich Danych**
- Wyniki "Reverse Search" generują ogromną iterację na siedemdziesięciu miesięcznych wariantach. Odpowiedź zapisywana jest do Cache, optymalizując w ten sposób ponowne otwieranie.

**KROK 5: Prezentacja Użytkownikowi**
- Zwrócenie stawki do systemu dla analityka: Wyniki trafiają w wysoce estetycznym, przykuwającym uwagę frontendowym panelu zbudowanym za pomocą frameworku `React`. 

---

## 2. Architektura i Zależności Technologiczne (Dependencies)

### Frontend (User Interface)
Środowisko to `React 19` na bundlerze `Vite`, posługujący się czystwym i restrykcyjnie otypowanym językiem źródłowym `TypeScript`. Architektura zakłada użycie standardów designu klasy premium (glassmorphism/dark mode z paletami błękitu i szlachetnych szarości) stosując:
- **Tailwind CSS v4** + Mieszanie komponentów UI za pomocą **Material UI (MUI)**.
- Biblioteka ikonek z **@mui/icons-material**.
- Silnik nawigacji **React Router DOM v7**.
- Biblioteki narzędziowe: Zustand (Zarządzanie stanem - useAppStore), framer-motion (animacje fluidyczne), PDFJS/React PDF.
- Komunikacja REST: **Axios** oraz dedykowany `@supabase/supabase-js`.

### Backend (The Edge API Engine)
Środowisko to `Python 3.12` zarządzany i izolowany za pomocą menadżera repozytorium zależności `Poetry`. 
- Główne ramię aplikacji jest uruchomione jako **FastAPI** zarządzane serwerem ASGI **Uvicorn** / Granian. 
- Struktury obiektów definiowane przez pakiety walidacji i parsowania JSON znane jako **Pydantic**.
- Model analityki to wielkie wykorzystanie **Pandas** oraz **numpy**, współpracujące przy odczytach danych ubezpieczeń pochodzących z **Openpyxl/XLSX**.
- Środowisko AI: Google Generative AI (`google-genai`).
- Scraper'y omijające firewall (tzw. "Bypass Cloudflare Bot Protection"): pakiet **playwright-stealth** a szczególnie wbudowany modułowy **DrissionPage**.

---

## 3. Bazy Danych i Caching (Zarządzanie Stanem)

**A. SUPABASE POSTGRESQL (ONLINE DB):**
Jedyna, centralna, chmurowa instancja "Single Point of Truth" trzymana na zewnętrznym DataCenter Supabase dla bezpieczeństwa i stabilności pod adresacją API *gnpsdiarmwvqhqbyetce*. Tabele w niej przechowywane stanowią serce matryc algorytmów np. tabelka wskaźników utraty wartości bazy modeli SAMAR, koszty serwisowania w zależności od wielkości pojazdów itp. 
Bezpośredni kontakt oparty jest z 2 płaszczyzn:
- **Frontend** odpytuje bezpośrednio klientem `@supabase-js` proste, publiczne słowniki aut bez zapytań do serwera (upraszczając zapytania typu "Dropdown Menu").
- **Backend** odpytuje krytyczne logiki, uwzględniając mechanizm uprawnień RLS oraz pule podzapytań na portach poprzez uwierzytelniony `supabase_client`.

**B. REDIS (LOCAL KVS DOCKER):**
Architektura w oparciu na serwer `Redis` uruchamiany w dockerze za pośrednictwem `docker-compose.yml`. Służy jako `Data Broker` oraz `Cache Layer`. Odejmuje pracę bazie SQL przechowując czasowe zmienne sesji i tabele wielowymiarowe dla cenników "odwróconego wyszukiwania". 

---

## 4. Wykorzystywane Endpointy Sieciowe (API Endpoints w FastAPI)

W pliku startowym `backend/main.py` serwer rejestruje wysoce modułowy system ścieżek "Routerów" (pod zwięzłym prefixem `/api/`):
- `/api/samar_rv` → Działający z silnikami SAMAR_RV dla modeli cennikowych (samar_rv_routes).
- `/api/parser` ; `/api/extract` ; `/api/pdf_parser` → Obsługa wręczania żądań "Extraction Pipeline" dla GenAI dokumentu. 
- `/api/kalkulacje` ; `/api/calculator_core` → Centrum Matematyczne silników wykonujących kalkulacje kaskadowe LTR_Kalkulator oraz "Calculate Endpoint" dla pojedynczego matrixa.
- `/api/scoring_search` → Panel podbioru wyników wyciąganych po Scoring'u rentowności. Szukaj samochodu od "Zadań Ceny Bazowej" ujemnie doliczanej marży.
- `/api/oferty` (`/api/offers`) → Zarządzanie tworzeniem listów ze zliczonymi modelami kalkulatora, z możliwościami dodawania po koszyku handlowca.
- Różne instancje routerów CRUD Admina: Przykładowo `/api/config_crud`, `/api/features_crud`, `/api/control_center_admin`, zajmujące się operacjami zapisywania konfiguracji (Zależności "No Hardcode"). Cechą ujednoliconą aplikacji jest brak konieczności edycji softu podczas nowej marki, tylko wprowadza się wiersz do tabel w oparciu przez interfejs `/control-center`.
- `/api/sheets_sync` → Zewnętrznych Integratyw API za pomocą pakietów `gspread`, które synchronizują nowe tabele.

---

## 5. Background Tasks i Operacje Asynchroniczne w Tle

Jako że kalkulacja PDF-a, pobieranie cache z Supabase czy renderowanie AI trwają od `2s do 35s`, uśmierciłyby serwer standardowego FastApi blokując kolejkę na porcie. Do tego wykorzystywane jest oddelegowanie "Twardych Obliczeń" (*Celery Background Tasking*):
1. Serwer wyrzuca obiekt polecenia na serwer `Redis` do "Kolejki Żądań".
2. Wymagane jest uruchomienie **Workerów Celery** poleceniem `celery -A core.celery_app worker --pool=solo` co powoduje wywołanie cichych demonów obliczeniowych na backendzie. Wątki te (zdefiniowane dla `PDF` na dyspozytorach w tle) pobierają obiekt do uderzenia przez `Vertex`.
3. Worker pracuje w tle wysyłając dane do API AI/Vertex. 
4. Celery po wysłaniu wywołania posiada mechanizm **Anulowania zapytań** (`threading.Event`). W panelu wyświetlania Frontendu wprowadzony jest wskaźnik "Stepper" ze słowem "Anuluj Processing", co natychmiast przerywa opłatę zużycia tokenów do wirtualnych sieci Google przez `register_cancel_event`.

---

## 6. Główna Architektura Widoków Frontendu i Funkcjonalności 

Poszczególne trasy zaimplementowane pod skrzydłem biblioteki `React Router DOM` z warunkoaniem stanu przez Context Providers `Zustand`:

> Głółwny Header (Stick Navigation) zawiera przyciski, by wywołać **Skrót z klawiatury Command Palette zagnieżdżonej (Ctrl+k)** oraz panel "Koszyka" w rogu okna.

1. **Widok Ekstrakcja i Analiza AI (`/`) -> `<VertexExtractorPage />`** 
   - Główny pion wejściowy pracy programu. Widok przeznaczony dla Uploadów Plików, posiada "Drag & Drop".
   - Kiedy dodasz PDF wywoływane stają się w tle Joby `Background Tasks`.
   - Zintegrowane karty wyświetlania (Digital Twin) pobrane i odtworzone jako model danych od AI pokazują precyzyjnie wypunktowane wyciągniete parametry, dając szansę ocenie przez człowieka błędu maszyny przed wrzuceniem do Kalkulatora Kosztów.

2. **Widok Biblioteka Cenników (`/library`) -> `<CatalogLibraryPage />`**
   - Środowisko udostępniania katalogów dealerskich ułożonych kafelkowo wraz z wgranymi specyfikacjami. Pozwala w sposób wizualnie atrakcyjny przeszukać i zarządzać plikami do przeliczania dla nowych ofert. Używane tu formaty i filtry na komponentach MUI z palety barw Gradientowych i dynamicznych Hoverów.

3. **Widok Wyszukiwarka / Scoring (`/search`) -> `<ScoringSearchPage />`**
   - Panel analityczny dla menadżerów z pytaniem biznesowym *"Jakiego Porschę oferujemy przy stałej Raty na marży 12% kwotowo do 6 tysięcy miesięcznie"*. Odwrócona weryfikacja - program zaczytuje dane Cached, pomija koszt obliczeń kaskady, po czym uwidocznia w układach Data-Gridów wyrenderowane pasujące warianty rocznikowe, dodające i nakładające precyzyjnie marżę dopiero "On View" po stronie aplikacji na podstawie zadeklarowanej na ekranie "supełkiem" marży. 

4. **Widok Sync Google Sheets (`/sheets-sync`) -> `<SheetsSyncPanel />`**
   - Miejsce pracy operatora w celu hurtowej aktualizacji konfiguracji kosztowych, bazujące w synchronizację autozbiorczą poprzez pakiety logowania google tokenami `gspread`. Wgrywa poprawne cenniki ubezpieczeń (i tak ukierunkowane opcje bazy). Podzielone na karty widokujące akcję "Sync Down".

5. **Widok Control Center / Admin (`/control-center`) -> `<ControlCenter />`**
   - Serce całej reguły z architektury *"ZERO-HARDKODOWANIA"*. Strona dzieli się na dziesiątki specjalnych Zakładek (`Tabs`), w których każda to oddzielny CRUD obsługi konkretnej tabeli bazy Supabase w interfejsie formularzy na froncie:
     - **Tabele Cech Systemowych & Mnożników (Multiplayers):** `BrandCorrectionCrud`, `BodyTypesCrud`, `EnginesCrud`,  `PaintCorrectionCrud` oraz `SamarMasterPanel`. Tutaj analityk w panelach read/write koryguje o minus % na markach premium albo dodaje współczynniki ubezpieczeń.
     - **Tabela Algorytmów LTR:** Parametryzacje SubKalkulatorów zawartych poniżej z bazami m.in Kosztów usług serwisów flotowych (`ServiceCostsCrud`), `TransportFeesCrud` (Stawki Logistyków), Kosztami Aut Zastępczych (`ReplacementCarCrud`) czy stawką opon wielosezonowych (`TabelaOponCrud`).
     - Global Settings – do ręcznej weryfikacji po resecie lub załadowaniach awaryjnych logik "Global Settings Panel". Wszystkie komponenty zostały poddane sztywnym regułom `Zero-Fallbacks` – oznacza to, że jeśli wykasujesz z panelu parametr wymagany dla marki, system dla marki wywali ostrzeżenie na produkcję.
