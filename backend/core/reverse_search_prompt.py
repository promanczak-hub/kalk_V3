"""Dynamic prompt builder for Reverse Search LLM extraction.

Replaces the previously-hardcoded REVERSE_SEARCH_SYSTEM_PROMPT with a prompt
built from the live catalog (`reverse_search.universal_features`). The catalog
is the source of truth — synced from Google Sheet 'cechy' via mdm_sync.py.
"""

from __future__ import annotations

from collections import defaultdict

from core.feature_catalog_loader import (
    CatalogFeatureEntry,
    load_filterable_features,
)


_PROMPT_HEADER = """\
# SYSTEM PROMPT: Reverse Search Feature Extractor (multi-type)

## ROLA
Jesteś inżynierem danych motoryzacyjnych. Z wejścia (tekst, mail klienta, fragment SIWZ
lub nagranie głosowe) wyciągasz wymagania klienta i mapujesz je 1:1 na ustandaryzowany
katalog cech podany niżej. Katalog jest jedynym źródłem prawdy — nie wymyślaj kluczy.

## ZASADY EKSTRAKCJI (KRYTYCZNE)

1. **TYLKO klucze z katalogu.** Każdy `feature_key` w odpowiedzi MUSI istnieć na poniższej
   liście. Klucze spoza katalogu zostaną odrzucone przez backend.
2. **Dobierz typ wartości do `feature_type` cechy:**
   - `boolean`: ustaw `value_bool=true` GDY klient jawnie tego wymaga. Nie używaj false —
     brak wymagania = pomiń cechę.
   - `numeric`: ustaw `value_num=<liczba>` oraz `op` (`gte`, `lte` lub `eq`). Konwertuj
     jednostki na canonical (np. "30 tys km" → 30000, "3.5 t" → 3500 jeśli jednostka kg).
   - `text` / `enum`: ustaw `value_text=<wartość>`. Dla enum dopuszczone wartości są
     w nawiasie `dozwolone:` (jeśli podane).
3. **Operatory dla numeric:**
   - "minimum X", "co najmniej", "od X" → `op=gte`
   - "max X", "do X", "nie więcej niż" → `op=lte`
   - "dokładnie X" → `op=eq`
4. **Kontekst pojazdu (applies_to):** Jeśli z zapytania wynika typ pojazdu (osobowy / LCV /
   ciężarowy), pomiń cechy nieadekwatne — w katalogu masz tag `pojazdy:[...]`. Pusta lista
   = uniwersalne.
5. **Brak danych = pomiń.** Nie zgaduj. Pewność < 80% → pomiń cechę.
6. **Rozpakowywanie pakietów:** "Pakiet Zimowy", "Pakiet Comfort" → rozpisz na konkretne
   boolean cechy z katalogu (np. heated_front_seats, heated_steering_wheel).
7. **Synonimy:** w katalogu masz `synonimy:[...]` na każdej cesze — używaj ich jako
   dodatkowych form rozpoznania, nie tylko `display_name`.
8. **Reverse Search context:** klient mówi czego POTRZEBUJE w aucie. Cechy poniżej
   to lista filtrowalnych (`is_active AND is_filterable`).

## POLA FINANSOWE (poza katalogiem cech)

- `price_max`: maksymalna miesięczna rata netto w PLN. Brak → null.
  **Jeśli klient poda kwotę w EUR/USD, przelicz na PLN** (kurs: 1 EUR ≈ 4.30 PLN, 1 USD ≈ 4.00 PLN).
  Przykład: "650 EUR/mc" → 2795. "Budżet 2500-2700 zł" → 2700 (górna granica). "do 2500" → 2500.
- `duration_months`: czas leasingu w miesiącach. "4 lata" → 48. Brak → null.
- `annual_mileage`: roczny limit kilometrów. "30 tys" → 30000. Jeśli klient podaje na
  cały okres ("160 tys przez 4 lata"), oblicz roczny limit (160000/4 = 40000). Brak → null.

## POLA POJAZDÓW (poza katalogiem cech)

- `brands`: lista marek wymienionych przez klienta. **Zwracaj kanoniczne nazwy:**
  "WV"/"VW"/"Volkswagen" → "Volkswagen". "Mercedes"/"MB" → "Mercedes-Benz".
  Przykład: "Skoda Kodiaq lub VW Tayron, ewentualnie Volvo XC60" → ["Skoda", "Volkswagen", "Volvo"].
  Brak marek → null.
- `models`: lista modeli (sama nazwa, bez marki i bez wersji silnikowej).
  "Skoda Kodiaq Drive 2.0 TSI 204KM" → "Kodiaq". "Hyundai Tucson 2025/2026" → "Tucson".
  "VW Tayron"/"Volkswagen Tayron" → "Tayron". "Volvo XC40 lub XC60" → ["XC40", "XC60"].
  Przykład pełny: ["Kodiaq", "Superb", "Tucson", "XC40", "XC60", "Tayron", "Passat"].
  Brak → null.

## WEJŚCIE AUDIO

Jeśli wejściem jest plik audio, w polu `transcript` zwróć dosłowną transkrypcję wypowiedzi
po polsku (zachowaj naturalne sformułowania, popraw oczywiste przejęzyczenia). Cechy
ekstraktuj na podstawie tej transkrypcji. Dla wejścia tekstowego pozostaw `transcript=null`.

## KATALOG CECH (jedyne źródło prawdy)
"""


def _format_feature_line(f: CatalogFeatureEntry) -> str:
    """Format a single feature entry for the prompt."""
    parts: list[str] = [f"* `{f.feature_key}` ({f.display_name})"]
    parts.append(f"[typ: {f.feature_type}]")

    if f.canonical_unit:
        parts.append(f"[jednostka: {f.canonical_unit}]")

    if f.allowed_values:
        vals = ", ".join(f.allowed_values[:8])
        if len(f.allowed_values) > 8:
            vals += "..."
        parts.append(f"[dozwolone: {vals}]")

    if f.trigger_keywords:
        kws = ", ".join(f.trigger_keywords[:6])
        parts.append(f"[synonimy: {kws}]")

    if f.applies_to_vehicle_categories:
        parts.append(f"[pojazdy: {', '.join(f.applies_to_vehicle_categories)}]")

    if f.applies_to_body_subtypes:
        bodies = ", ".join(f.applies_to_body_subtypes[:4])
        if len(f.applies_to_body_subtypes) > 4:
            bodies += "..."
        parts.append(f"[nadwozia: {bodies}]")

    if f.applies_to_powertrains:
        parts.append(f"[napęd: {', '.join(f.applies_to_powertrains[:3])}]")

    if f.is_required_for_reverse_search:
        parts.append("[REQUIRED]")

    return " ".join(parts)


def _is_prefixed(feature_key: str) -> bool:
    """True if key uses one of the curated namespaces (eq_/spec_/dim_/opt_)."""
    return any(feature_key.startswith(p) for p in ("eq_", "spec_", "dim_", "opt_"))


def _dedup_by_display_name(catalog: list[CatalogFeatureEntry]) -> list[CatalogFeatureEntry]:
    """Collapse duplicate display_names. Prefer prefixed (eq_*/spec_*/dim_*) over naked.

    The DB has historic duplicate rows where the same concept (e.g. ABS) has
    both `abs` and `eq_abs` keys, both flagged is_filterable. Showing both to the
    LLM costs tokens and risks double-counting if the LLM returns both keys.
    """
    by_name: dict[str, CatalogFeatureEntry] = {}
    for f in catalog:
        key = f.display_name.strip().lower()
        existing = by_name.get(key)
        if existing is None:
            by_name[key] = f
            continue
        # Prefer prefixed over naked.
        if _is_prefixed(f.feature_key) and not _is_prefixed(existing.feature_key):
            by_name[key] = f
    return list(by_name.values())


def build_reverse_search_prompt() -> str:
    """Build the full system prompt from the live catalog."""
    raw = load_filterable_features()
    catalog = _dedup_by_display_name(raw)
    if not catalog:
        return _PROMPT_HEADER + "\n(Katalog pusty — żadne cechy aktywne i filtrowalne.)\n"

    by_category: dict[str, list[CatalogFeatureEntry]] = defaultdict(list)
    cat_order: dict[str, int] = {}
    for f in catalog:
        by_category[f.category_name].append(f)
        cat_order.setdefault(f.category_name, f.category_sort)

    sections: list[str] = [_PROMPT_HEADER, ""]
    dedup_note = (
        f" (po deduplikacji z {len(raw)} wpisów)" if len(catalog) < len(raw) else ""
    )
    sections.append(
        f"**Liczba aktywnych cech filtrowalnych: {len(catalog)}**{dedup_note}\n"
    )

    for cat_name in sorted(by_category.keys(), key=lambda c: (cat_order.get(c, 999), c)):
        sections.append(f"### {cat_name}")
        for f in by_category[cat_name]:
            sections.append(_format_feature_line(f))
        sections.append("")

    return "\n".join(sections)
