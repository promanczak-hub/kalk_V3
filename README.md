# Kalk v3 (Kalkulator LTR V2)

Zaawansowana aplikacja do kalkulacji leasingu/najmu pojazdów z wbudowanym systemem inteligentnej ekstrakcji danych z dokumentów (np. ofert PDF) za pomocą modeli AI.

## 🛠 Technologie

Projekt składa się z dwóch głównych części – nowoczesnego interfejsu w React oraz szybkiego API napisanego w FastAPI.

### Frontend

- **Framework:** React 19 + Vite
- **Stylizacja:** Tailwind CSS v4 + Material UI (MUI)
- **Routing:** React Router DOM v7
- **Baza/Autoryzacja:** Supabase Client

### Backend

- **Framework:** FastAPI (Python 3.12+)
- **Zarządzanie pakietami:** Poetry
- **Baza danych:** Supabase (instancja chmurowa / online)
- **Sztuczna Inteligencja:** Google GenAI (Vertex AI / Gemini) do procesowania plików PDF
- **Przetwarzanie danych:** Pandas, Openpyxl

## ☁️ Baza danych — Supabase Online

**Link do projektu (Dashboard):** [https://supabase.com/dashboard/project/gnpsdiarmwvqhqbyetce](https://supabase.com/dashboard/project/gnpsdiarmwvqhqbyetce)

> [!IMPORTANT]
> **Projekt korzysta z chmurowej (online) instancji Supabase** — NIE z lokalnego Dockera.
>
> Lokalna instancja Supabase (Docker) jest **niestabilna** i wielokrotnie powodowała utratę danych
> przy operacjach migracyjnych (`supabase db reset`, `supabase migration up`).
>
> **Reguły pracy z bazą online:**
>
> - Backend i frontend łączą się z instancją chmurową (klucze w `.env`).
> - **NIE** uruchamiaj `supabase db reset` — grozi utratą danych.
> - Zmiany schematu (DDL) aplikuj przez **SQL Editor** w Supabase Dashboard.
> - Przed destrukcyjnymi operacjami **zawsze** rób backup (`pg_dump` lub eksport XLSX z Control Center).
> - Traktuj dane w bazie online jako **dane produkcyjne**.

> [!CAUTION]
>
> ### 🤖 AI LOCKOUT — Blokada dla agentów AI
>
> Poniższe operacje SQL/MCP na bazie **ONLINE** (`gnpsdiarmwvqhqbyetce`) są **ZABRONIONE**:
>
> | Operacja                        | Status        |
> | ------------------------------- | ------------- |
> | `DELETE FROM ...`               | 🚫 ZABRONIONE |
> | `DROP TABLE / DROP COLUMN`      | 🚫 ZABRONIONE |
> | `TRUNCATE TABLE`                | 🚫 ZABRONIONE |
> | `supabase db reset` (online)    | 🚫 ZABRONIONE |
> | `apply_migration` z DROP/DELETE | 🚫 ZABRONIONE |
>
> **Dozwolone:** `SELECT`, `INSERT`. `UPDATE` tylko po wyraźnej komendzie użytkownika.
>
> **Procedura:** Jeśli użytkownik wyraźnie każe usunąć dane → STOP → powtórz komendę → czekaj na potwierdzenie.

## 🚀 Uruchomienie lokalne

### 1. Wymagania wstępne

- Node.js (v20+)
- Python 3.12+
- Poetry
- Konto Supabase (klucze API w `.env`)

### 2. Konfiguracja zmiennych środowiskowych

Utwórz pliki `.env` w odpowiednich katalogach (patrz sekcja `.env.example` lub skontaktuj się z zespołem po klucze).

Dla backendu niezbędne mogą być zmienne dla Supabase oraz Google GenAI (Vertex AI).

### 3. Uruchomienie Backendu

```bash
cd backend
poetry install
poetry run python main.py
```

> API będzie dostępne pod adresem: `http://localhost:8000`

### 4. Uruchomienie Frontendu

```bash
cd frontend
npm install
npm run dev
```

> Aplikacja webowa będzie dostępna pod adresem: `http://localhost:5173`

## 🧪 Testy i Standardy Kodu

Projekt kładzie duży nacisk na jakość kodu. Przed commitem upewnij się, że kod przechodzi wszystkie formatowania, lintery i testy.
Zasada krytyczna: **Żaden plik z kodem źródłowym (komponenty, serwisy, kontrolery, API) nie może przekraczać 400 linii kodu.** Moduły dłuższe podlegają bezwzględnej refaktoryzacji na mniejsze jednostki/komponenty.

W folderze `backend/`:

- **Formatowanie:** `poetry run black .` oraz `poetry run isort .`
- **Linter:** `poetry run ruff check .`
- **Typowanie:** `poetry run mypy .`
- **Testy jednostkowe/integracyjne:** `poetry run pytest`

### 🔄 Testy Dwukierunkowe (Zmiany wpływające na Bazę Danych)

Jeśli jakakolwiek akcja lub wprowadzana modyfikacja w aplikacji ma wpływ na bazę danych (np. dodanie nowej logiki zapisu, operacje CRUD, zmiana struktury pól, nowy endpoint mutujący), **bezwzględnie wymagane jest zaplanowanie i wykonanie testu dwukierunkowego**.

**Zasady testu dwukierunkowego:**
1. **W przód (Zapis / Mutacja):** Należy potwierdzić (testem manualnym lub automatycznym), że aplikacja potrafi poprawnie utworzyć lub zaktualizować rekord w bazie, a zserializowany payload odpowiada schematowi (np. uderzenie do API skutkuje dodaniem poprawnego wiersza w Supabase bez zgubionych danych).
2. **W tył (Odczyt / Rekonstrukcja stanu):** Bezpośrednio po udanym zapisie, należy odpytać bazę o ten sam zasób i udowodnić, że system potrafi go bezbłędnie odebrać, zdeserializować i wyświetlić (np. pobranie dodanego zasobu przez React Query i pełne, poprawne wyrenderowanie go bez błędów w konsoli).

**Cel:** Eliminacja bolesnych błędów typu "write-only", w których zapis kończy się statusem 200 OK, ale ukryty błąd w nazwach pól lub typach sprawia, że przy pierwszej próbie ponownego załadowania widoku, aplikacja "wysypuje się" podczas parsowania (np. FastAPI/Pydantic rzuca wyjątek walidacji lub UI "wybucha" renderując `undefined`).

## 🤝 Kontrybucja

1. Skonfiguruj środowisko lokalne zgodnie z wytycznymi w pliku `SKILLS.md`.
2. Każda nowa funkcja powinna zawierać odpowiednie testy jednostkowe (`tests/`).
3. Stosuj rygorystyczne typowanie funkcji (`typing`, `pydantic`).

## 🤖 Instrukcja (Prompt) dla Twojego IDE

Skopiuj i dostosuj poniższy prompt. Wklej go na początku sesji (np. w Cursorze jako "Rules for this chat" lub w Composerze):

> Rola: Jesteś ekspertem od refaktoryzacji systemów legacy i logiki matematycznej. Naszym zadaniem jest migracja logiki przeliczeniowej ze starego kalkulatora do nowej architektury.
>
> Zasady współpracy (KRYTYCZNE):
>
> 1. Planowanie i Implementation Plan: Zanim napiszesz jakikolwiek kod lub wprowadzisz nową funkcjonalność, przygotuj szczegółowy plan wdrożenia (Implementation Plan) podzielony na mikrokroki. Wprowadzenie i modyfikacja KAŻDEJ funkcji musi być poprzedzona zapytaniem i akceptacją tego planu.
> 2. Zasada Stopu: Po każdym pojedynczym kroku (np. analiza jednej funkcji, stworzenie jednego testu) musisz się zatrzymać i wyświetlić podsumowanie: "Co zostało zrobione" oraz "Co jest planowane w następnej kolejności".
> 3. Weryfikacja: Czekaj na moją komendę "Dalej", "Kontynuuj" lub "Popraw", zanim przejdziesz do wykonywania kolejnego punktu planu. Nigdy nie wykonuj kilku kroków naraz.
> 4. Aktywne Pytanie: Jeśli w starej logice występuje niejasność, brak dokumentacji lub ryzyko błędu zaokrągleń – nie zgaduj. Zatrzymaj się i natychmiast zapytaj mnie o intencję biznesową lub dostarczenie większego kontekstu.
> 5. Test-First (TDD): Każdy krok logiki musi być poprzedzony stworzeniem testu jednostkowego, który potwierdza zgodność starego wyniku z nowym. Dopiero po przejściu (lub napisaniu) testu, możesz zaimplementować docelowy kod funkcji.

## 🔢 Kolejność Sub-Kalkulatorów (V1 → V3)

Kanoniczna kolejność uruchamiania sub-kalkulatorów w pipeline `LTRKalkulator.Calculate()`.
Źródło: `C:\Users\proma\Downloads\kalkulator_V1_extracted\kalkulator_V1\LTRKalkulator.cs` (linie 250-398).

| #   | Skrót (V1) | Sub-Kalkulator           | Plik V3 (Python)                        | Zależności wejściowe     |
| --- | ---------- | ------------------------ | --------------------------------------- | ------------------------ |
| 1   | **(Op)**   | **Opony**                | `LTRSubCalculatorOpony.py`              | — (niezależny)           |
| 2   | **(KDod)** | **Koszty Dodatkowe**     | `LTRSubCalculatorKosztyDodatkowe.py`    | — (niezależny)           |
| 3   | **(SZst)** | **Samochód Zastępczy**   | `LTRSubCalculatorSamochodZastepczy.py`  | — (niezależny)           |
| 4   | **(Srw)**  | **Serwis**               | `LTRSubCalculatorSerwisNew.py`          | — (niezależny)           |
| 5   | **(CeZ)**  | **Cena Zakupu (CAPEX)**  | `LTRSubCalculatorCenaZakupu.py`         | Opony (koszt 1 kpl)      |
| 6   | **(UtW)**  | **Utrata Wartości (WR)** | `LTRSubCalculatorUtrataWartosciNew.py`  | CenaZakupu               |
| 7   | **(Am)**   | **Amortyzacja**          | `LTRSubCalculatorAmortyzacja.py`        | CenaZakupu, WR           |
| 8   | **(Ub)**   | **Ubezpieczenie**        | `LTRSubCalculatorUbezpieczenie.py`      | Amortyzacja%, CenaZakupu |
| 9   | **(Fi)**   | **Finanse (PMT)**        | `LTRSubCalculatorFinanse.py`            | CenaZakupu, WR           |
| 10  | **(KDz)**  | **Koszt Dzienny**        | `LTRSubCalculatorKosztDzienny.py`       | Wszystkie powyższe       |
| 11  | **(St)**   | **Stawka**               | `LTRSubCalculatorStawka.py`             | KosztDzienny + wszystkie |
| 12  | **(Bm)**   | **Budżet Marketingowy**  | `LTRSubCalculatorBudzetMarketingowy.py` | WR                       |

> [!IMPORTANT]
> **Kroki 1–4** są niezależne — mogą być liczone równolegle.
> **Kroki 5–9** mają zależności kaskadowe (każdy zależy od poprzednich).
> **Kroki 10–12** agregują wyniki wszystkich poprzednich.

---

## 🗄️ Rejestr Nazw Tabel Supabase

> [!CAUTION]
> **Nazwy tabel DB, backendu i frontendu MUSZĄ być zsynchronizowane.**
> Każda zmiana nazwy wymaga jednoczesnej aktualizacji we WSZYSTKICH warstwach.

**Centralny rejestr:** [`TABLE_REGISTRY.md`](TABLE_REGISTRY.md)

Zawiera:

- Pełną mapę: **nazwa tabeli DB → pliki backend → pliki frontend**
- Procedurę Impact Analysis (grep + sprawdzenie widoków SQL)
- Checklist zmiany nazwy (7 kroków)

**Reguła dla AI/developerów:** Przed zmianą nazwy tabeli, kolumny lub widoku:

1. Otwórz `TABLE_REGISTRY.md` i zlokalizuj wszystkie zależne pliki
2. Wykonaj `grep -rn "nazwa" backend/ frontend/src/` aby potwierdzić
3. Zaktualizuj WSZYSTKIE warstwy w jednym commicie
4. Zaktualizuj `TABLE_REGISTRY.md`

---

## 📋 Changelog & Śledzenie Zmian API

Sekcja dokumentuje istotne zmiany w interfejsach, modułach i funkcjach projektu.
Celem jest zapewnienie pełnej transparentności — szczególnie gdy istniejąca funkcjonalność
jest usuwana, zastępowana lub zmienia sygnaturę.

### Konwencja wpisów

- 🆕 `[NEW]` — nowa funkcja/moduł/endpoint
- ♻️ `[CHANGED]` — zmiana sygnatury, zachowania lub nazwy
- 🗑️ `[REMOVED]` — usunięta funkcja (z podaniem powodu i zamiennika)
- 🐛 `[FIXED]` — poprawka błędu
- ⚠️ `[DEPRECATED]` — oznaczone do usunięcia w przyszłej wersji

### Historia zmian

#### 2026-03-04 — Progress Tracking & Cancel w pipeline

- `[NEW]` `POST /api/cancel-processing` — endpoint do natychmiastowego anulowania przetwarzania dokumentu
- `[NEW]` `core/background_jobs.py: register_cancel_event`, `trigger_cancel` — registry wątków z `threading.Event`
- `[CHANGED]` `core/background_jobs.py: process_and_save_document_bg` — dodano aktualizację `verification_status` po każdym etapie pipeline'u (`uploading`, `extracting_twin`, `generating_summary`, `matching_discounts`, `mapping_data`) + sprawdzanie flagi cancel przed kosztownymi wywołaniami LLM
- `[CHANGED]` `core/extractor_v2.py: extract_vehicle_data_v2` — nowe opcjonalne parametry `on_progress` i `is_cancelled` (callbacks)
- `[CHANGED]` `VehicleRowCard.tsx` — zamiana prostego spinnera na stepper z 5 etapami + przycisk "Anuluj"
