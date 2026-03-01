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

## 🧪 Testy

Projekt kładzie duży nacisk na jakość kodu. Przed commitem upewnij się, że kod przechodzi wszystkie formatowania, lintery i testy.

W folderze `backend/`:

- **Formatowanie:** `poetry run black .` oraz `poetry run isort .`
- **Linter:** `poetry run ruff check .`
- **Typowanie:** `poetry run mypy .`
- **Testy jednostkowe/integracyjne:** `poetry run pytest`

## 🤝 Kontrybucja

1. Skonfiguruj środowisko lokalne zgodnie z wytycznymi w pliku `SKILLS.md`.
2. Każda nowa funkcja powinna zawierać odpowiednie testy jednostkowe (`tests/`).
3. Stosuj rygorystyczne typowanie funkcji (`typing`, `pydantic`).
