# 🧬 Semantyczny Cyfrowy Bliźniak: Kalk v3

Ten dokument jest żywym opisem architektury i logiki aplikacji. Jest aktualizowany przy każdej zmianie systemowej.

## 🏗️ 1. Natura Projektu (Stan Obecny)

Kalk v3 to system kalkulacyjny umożliwiający zarządzanie wycenami pojazdów. Główne fukcjonalności obejmują:

- Pobieranie danych leasingowych/kredytowych.
- Integrację poprzez API FastAPI na backendzie.
- Dynamiczny frontend stworzony w oparciu o React, Vite, Tailwind CSS 4 i wybrane elementy MUI.
- Zarządzanie stanami bazy danych poprzez Supabase (baza PostgreSQL oparta na chmurze).

## ⚙️ 2. Mechanika "Pod Maską"

### Ekstrakcja Danych (AI Pipeline) 🤖

- **Narzędzie Główne**: Integracja z modelami z rodziny **Google Gemini 2.5 Pro** (dostęp do nich odbywa się natywnie za pomocą biblioteki `google-genai` w Pythonie).
- **Proces Ekstrakcji**:
  - Plik (zazwyczaj oferta samochodu np. PDF) trafia na endpoint `/api/extract/...`.
  - Przekazywany jest do wyspecjalizowanej usługi (`ExtractorV2` używającej klasy `DocumentProcessor` i modelu `gemini-2.5-pro`).
  - Używa zaawansowanego `System Prompt` dopasowanego do polskiego rynku motoryzacyjnego.
  - Wyjściowy JSON (z czyszczeniem potencjalnych błędów formatowania modelu) mapuje parametry techniczne (moc, silnik, rodzaj napędu), składowe ceny (cena bazowa, opcje dealerskie, rabaty) na spójne dane.

### Walidacje Certyfikacyjne

- Posiada wbudowaną weryfikację logiki leasingów/finansów, rabatów. Sprawdza poprawność zsumowanych wartości oraz wylicza tzw. TCO (Total Cost of Ownership), w tym koszty rat, wykupów, ubezpieczenia (Assistance/OC/AC) oraz ogumienia.
- Operacje wyciągania powiązane są z wartościami rezydualnymi dla platformy **SAMAR** (mapowanie klasy pojazdu).

## 📊 3. Struktura Danych (Semantic Schema)

Główne obiekty przesyłane pomiędzy frontendem a backendem zostały zdefiniowane w Pydantic (szczegóły: `backend/core/parser_schema.py` i inne).

### Przykładowy Cyfrowy Bliźniak Oferty (`MappedOffer`):

- `brand` i `model` kluczowe dane określające pojazd.
- `body_style`, `segment`, `samar_class_name` klasyfikacja (zmapowana wewnetrzenie na silnik reguł SAMAR).
- `fuel_type`, `transmission`, `power_hp`, `tire_size`.
- **Ceny**: `base_price_net`, wektory `factory_options` oraz `dealer_options` (własność typu `MappedOption` trzymająca nazwę i cenę składową).
- **Rabaty**: `discount_amount_net` albo wyliczony `discount_pct`.

### Inne obiekty domenowe

- Obserwowana jest zaawansowana logika _budżetowa_ oraz kalkulacyjna (Leasing / Najem), zarządzana w backendzie (`engine_v3.py`, pobieranie ubezpieczenia czy kosztów pobocznych).

## 🔌 4. Integracje, Zależności i Architektura

- **Frontend:** Single Page Application oparta o Vite do renderowania UI. Czysta komunikacja po HTTPs za pomocą biblioteki Axios.
- **Backend:** FastAPI pełniące rolę szybkiego serwera opartego o Pydantic, zajęte przede wszystkim pośredniczeniem miedzy API LLM-ów, obsługą plików, a frontendem.
- **Baza Danych (Supabase):** Dostęp do niej realizowany poprzez wbudowanego klienta supabase w Pythonie i Reactie. Baza prawdopodobnie przetrzymuje wyekstrahowane dane i zapisy utworzonych Kalkulacji, pozwalając na powrot do historii, rezydualne modyfikacje w cenniku (discount overrides/budgets), by nie wypytywać za każdym razem Gemini Pro dla tego samego PDFA.
- **Ciągły rozwój testowania:** Aplikacja od strony backendu jest pokryta testami używając `pytest` z asynchronicznymi modułami i mocnymi assercjami integracyjnymi (`test_end_to_end.py`, `test_extractor.py`).

---

_Ostatnia aktualizacja:_ 2026-03-01
_Zmieniono:_ Inicjalizacja dokumentu Digital Twin na podstawie obecnej struktury plików.
