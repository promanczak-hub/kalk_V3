# Audyt stabilności aplikacji — 2026-04-28

**Metoda:** exploratory Playwright (headless Chromium), 1 worker, 47.6s.
Skrypt: [tests/e2e/audit.spec.ts](../tests/e2e/audit.spec.ts).
Surowe znaleziska: [findings.json](findings.json) (365 wpisów; 289 to szum z testu rapid-tab-switch — anulowane request'y przy szybkim przełączaniu route'ów, ignorowane).

**Realnych znalezisk: 76**, w tym **2 prawdziwe bugi backendu** + 1 ostrzeżenie biblioteki + dużo aborted requests przy nawigacji.

---

## 🔴 P0 — Krytyczne (apka nie działa)

### 1. Wyszukiwarka / Scoring całkowicie nie działa — backend woła zdropowane RPC

Trasa `/search` rzuca **HTTP 500** na inicjalnym ładowaniu i każdym wyszukiwaniu.

**Endpoint:** `GET /api/scoring-search/initial-data` → 500 (`reverse_search.rpc_get_scoring_initial_data() does not exist`)
**Endpoint:** `POST /api/scoring-search/search` → 500 (`Could not find the function public.rpc_reverse_search(...)`)

#### Root cause (potwierdzone w prod Supabase)

Migracja **`20260427165548_drop_universal_features_module`** (zaaplikowana wczoraj, 2026-04-27) wykonała hard-delete całej infrastruktury Scoring Search:

```sql
-- 1. DROP FUNCTION IF EXISTS public.rpc_reverse_search, rpc_get_available_filters,
--    rpc_get_similar_vehicles, scoring_search_compute_matches, ... (9 funkcji)
-- 2. DROP SCHEMA IF EXISTS reverse_search CASCADE  -- 18 tabel, 4 widoki, triggery
-- 3. DROP TABLE IF EXISTS public.vehicle_matrix_cache CASCADE
```

Komentarz w migracji: *"HARD DELETE ... User confirmed: hard delete, no backup, dev environment."*

Następująca migracja `20260427165616_create_universal_features_v2` odtworzyła **tylko** `universal_features` — **nie odtworzyła** RPC ani schemy `reverse_search`.

#### Dwa skutki, które widzimy w audycie

1. **`public.rpc_reverse_search` nie istnieje** — backend dostaje czysty `function not found`.
2. **`public.rpc_get_scoring_initial_data` istnieje jako orphan wrapper** — pętla DROP w migracji nie wymieniła go po nazwie, więc przeżył. Ale jego ciało to:
   ```sql
   select reverse_search.rpc_get_scoring_initial_data();
   ```
   Schemat `reverse_search` poszedł `DROP CASCADE` → wewnętrzne wywołanie pada. Stąd error mówi `reverse_search.rpc_get_scoring_initial_data does not exist` zamiast `public.*`.

#### Stan na teraz w prod (zweryfikowane przez Supabase MCP)

```
schema reverse_search → tylko 2 funkcje (rpc_sync_classification_features, set_updated_at)
schema public        → rpc_get_scoring_initial_data (orphan wrapper, nie działa)
                       BRAK: rpc_reverse_search, rpc_get_available_filters, ...
```

Lokalny folder `supabase/migrations/` ma sporą część migracji z marca/kwietnia (np. `optimize_rpc_get_scoring_initial_data_v2`, `add_brand_counts_to_initial_data_rpc`) **nie zachowanych jako pliki** — istnieją w prod history, ale ich nie ma w repo. Czyli źródło prawdy do odbudowy to **historia migracji w prod**, nie repo.

#### Akcja — opcje

1. **Rollback migracji `drop_universal_features_module`** + wszystkich późniejszych — ryzykowne, prod ma już zmiany w `universal_features_v2`.
2. **Odbudowa z historii prod**: pobrać CREATE statementy dla wszystkich `rpc_reverse_search`, `rpc_get_available_filters`, `rpc_get_scoring_initial_data` itp. z migration history (`supabase_migrations.schema_migrations`), zapisać jako nową migrację `20260428xxxxxx_restore_scoring_search_rpcs.sql`, zaaplikować. **Rekomendowane.**
3. **Wyłączyć Scoring Search w UI** dopóki nie ma decyzji co z tym modułem (jeśli był celowo droppowany).

Pytanie do ciebie: czy `drop_universal_features_module` był celowy (Scoring Search miał odejść), czy ktoś dropnął za szeroko? Jeśli celowy — backend trzeba okroić; jeśli nie — odbudować.

---

## 🟡 P2 — Cosmetic / dev-warnings

### 2. AG Grid v33 — mieszane Theming API i CSS File Themes

**Trasa:** `/calculations` (Historia Kalkulacji).
```
AG Grid: error #239 Theming API and CSS File Themes are both used in the same page.
```
W v33 Theming API jest domyślny — łącznie z importem `ag-grid-community/styles/ag-theme-*.css` powoduje konflikt. Dziś tylko warning, w przyszłej wersji prawdopodobnie hard error.

**Akcja:** zdecydować jedną drogę i zostać przy niej. Sprawdź gdzie importowany jest CSS theme grida vs gdzie używany jest `theme=`/`themeQuartz`.

---

## ℹ️ Obserwacje (nie traktuję jako bugi)

### 3. `/api/homologation/verify` aborted ×25 na `/calculations`

To są `net::ERR_ABORTED` — czyli żądania anulowane (najczęściej przez React unmount lub `AbortController`). Wszystkie 25 wystąpień było przy jednym ładowaniu strony, co sugeruje **debounce/effect re-fire** w kalkulacji homologacji — komponent rerenderuje się N razy, każdy render pyta backend, każdy poprzedni request leci do abortu. Nie pada nic do usera, ale to marnotrawstwo.

**Akcja (opcjonalna):** jeśli te 25 requestów odpala się sekwencyjnie przy jednym otwarciu — przydałby się `useDebounce` lub guard po stable key.

### 4. `/api/param-preview` aborted ×8 na `/calculations` i `/`

Ten sam wzorzec: kalkulator otwiera listę pojazdów, każdy wiersz pyta o `param-preview` z innym zestawem (samar_class_id, brand, fuel, drive...), część leci abortem przy unmount. Nie krytyczne, ale spore rozproszenie requestów.

### 5. Pozostałe

- **Bogus route** (`/this/does/not/exist-...`) → poprawnie redirectuje na `/`. ✅
- **Empty PDF upload** → nie spowodował crash'a (komponent zachował się grzecznie). ✅
- **XSS/SQL junk w polu wyszukiwania** → input nie crashuje, choć i tak całe wyszukiwanie jest 500 (P0 #1).
- **Brak `pageerror` i `unhandledrejection`** w trakcie audytu — czyli runtime React jest stabilny, błędy backendu są łapane i logowane, nie wywalają aplikacji.

---

## Rekomendacje kolejnych kroków

1. **Najpierw P0** — naprawić Scoring Search (najprawdopodobniej brakująca migracja DB).
2. Powtórzyć audyt po fixie — ten sam skrypt można odpalać `npx playwright test audit.spec.ts`.
3. Jeśli chcesz głębiej: rozszerzyć skrypt o pełny upload PDF + ekstrakcję (potrzebny prawdziwy plik testowy).
4. Schedulowanie nocne — gdy fix gotowy, mogę podpiąć `mcp__scheduled-tasks__create_scheduled_task` na codzienny przebieg + raport tylko przy nowych findingach.
