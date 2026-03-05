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
- **Baza danych:** Supabase
- **Sztuczna Inteligencja:** Google GenAI (Vertex AI / Gemini) do procesowania plików PDF
- **Przetwarzanie danych:** Pandas, Openpyxl

## 🚀 Uruchomienie lokalne

### 1. Wymagania wstępne

- Node.js (v20+)
- Python 3.12+
- Poetry
- Konto / lokalne środowisko Supabase

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
