"""Dynamic SAMAR class mapper using KlasaSAMAR_czak dictionary + Gemini Flash.

Returns ALL candidates ranked by confidence (reranking model).
"""

import json
import logging
import os
import time
from typing import Tuple

from google.genai import types
from supabase import Client, create_client

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300  # 5 minutes
_samar_cache: dict = {"data": None, "ts": 0.0}


def _build_samar_client() -> Client:
    """Create a lightweight Supabase client for SAMAR lookups."""
    url = os.environ.get("VITE_SUPABASE_URL", "")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    return create_client(url, key)


def _fetch_samar_dictionary(client: Client) -> list[dict]:
    """Fetch SAMAR class dictionary rows from ``KlasaSAMAR_czak``.

    Returns a list of dicts: ``[{"klasa": "PODSTAWOWA D ŚREDNIA", "modele": "1. Alfa Romeo ..."}]``
    Uses in-memory cache with 5-minute TTL.
    """
    now = time.monotonic()
    if _samar_cache["data"] and (now - _samar_cache["ts"]) < _CACHE_TTL_SECONDS:
        logger.debug(
            "[SAMAR MAPPER] Using cached dictionary (%d rows)",
            len(_samar_cache["data"]),
        )
        return _samar_cache["data"]

    response = (
        client.table("KlasaSAMAR_czak")
        .select("col_1, col_8, col_9")
        .order("col_9")
        .execute()
    )
    rows: list[dict] = []
    for row in response.data:
        klasa = (row.get("col_1") or "").strip()
        modele = (row.get("col_8") or "").strip()
        if klasa and modele:
            rows.append({"klasa": klasa, "modele": modele})

    _samar_cache["data"] = rows
    _samar_cache["ts"] = now
    logger.info("[SAMAR MAPPER] Refreshed cache: %d rows", len(rows))
    return rows


def map_to_samar_class(
    brand: str,
    model: str,
    segment: str | None = None,
    body_style: str | None = None,
    trim: str | None = None,
    transmission: str | None = None,
    number_of_seats: int | None = None,
) -> Tuple[str, str, list[dict]]:
    """Dynamically classify a vehicle into SAMAR classes with reranking.

    Queries ``KlasaSAMAR_czak`` for the full dictionary, then asks
    Gemini Flash to rank ALL classes by probability.

    Returns
    -------
    tuple[str, str, list[dict]]
        ``(short_code, best_class_name, ranked_candidates)``
        where ``ranked_candidates`` is a list of
        ``{"klasa": "...", "confidence": 0.95}`` sorted desc.
        Falls back to ``("UNKNOWN", "INNE - WYMAGA RĘCZNEGO MAPOWANIA", [])``
        on error.
    """
    fallback: Tuple[str, str, list[dict]] = (
        "UNKNOWN",
        "INNE - WYMAGA RĘCZNEGO MAPOWANIA",
        [],
    )

    if not brand and not model:
        return fallback

    try:
        sb_client = _build_samar_client()
        samar_dict = _fetch_samar_dictionary(sb_client)
    except Exception:
        return fallback

    if not samar_dict:
        return fallback

    # Extract unique class names for the prompt
    unique_classes = list(dict.fromkeys(row["klasa"] for row in samar_dict))

    # Build a compact representation for the prompt
    dict_text = "\n".join(
        f"- {row['klasa']}: {row['modele'][:200]}" for row in samar_dict
    )

    prompt = f"""Jesteś ekspertem klasyfikacji pojazdów wg macierzy IBRM SAMAR 2025.

Oto PEŁNY słownik klas SAMAR wraz z przykładowymi modelami przypisanymi do każdej klasy:
{dict_text}

Pojazd do klasyfikacji:
- Marka: {brand}
- Model: {model}
- Wersja/Trim: {trim or "brak danych"}
- Skrzynia biegów: {transmission or "brak danych"}
- Typ nadwozia: {body_style or "brak danych"}
- Segment: {segment or "brak danych"}
- Ilość miejsc: {number_of_seats or "brak danych"}

ZADANIE: Oceń prawdopodobieństwo przynależności tego pojazdu do KAŻDEJ klasy z powyższego słownika.
Dla KAŻDEJ klasy przypisz confidence (0.0-1.0) — jak bardzo ten pojazd pasuje do danej klasy.
Szukaj marki i modelu w listach przykładowych modeli. Zwróć SZCZEGÓLNĄ uwagę na typ nadwozia oraz wersję. 
Na przykład, ten sam wiodący model (jak 'VW Crafter' lub 'Ford Transit') może występować jako auto dostawcze ("S. DOSTAWCZE I CIĘŻAROWE..." lub "DOSTAWCZE") 
w wariancie 'Furgon' / ciężarowym, albo jako auto osobowe/bus ("MINIBUS I MINIBUS" lub "VANY...") w wariancie 'Osobowy' / 'Tourneo'.
Zawsze bierz pod uwagę czy to osobówka, czy auto użytkowe/cargo.

KRYTYCZNE REGUŁY ROZRÓŻNIANIA (bezwzględnie przestrzegaj):
1. Jeśli typ nadwozia (body_style) to 'Furgon', 'Panel Van', 'Van dostawczy', 'Dostawczy', 'Cargo', 'Skrzyniowy', 'Podwozie' lub 'Chłodnia' — NIGDY nie klasyfikuj jako MINIBUS. Użyj odpowiedniej klasy dostawczej: 'S. DOSTAWCZE I CIĘŻAROWE CIĘŻKIE DOSTAWCZE', 'S. DOSTAWCZE I CIĘŻAROWE ŚREDNIE DOSTAWCZE' lub 'S. DOSTAWCZE I CIĘŻAROWE KOMBI VAN'.
2. Klasa MINIBUS I MINIBUS jest WYŁĄCZNIE dla wariantów osobowych (przeszklonych, z siedzeniami pasażerskimi), np. 'Tourneo', 'Kombi', 'Bus', 'Osobowy', 'Caravelle', 'Multivan'.
3. Jeśli wersja/trim zawiera słowa 'L1H1', 'L2H2', 'L3H2', 'L4H3' itp. (oznaczenia rozstawów/wysokości furgonów) — to ZAWSZE jest furgon dostawczy, nie minibus.
4. Jeśli ilość miejsc >= 6, rozważ klasy MINIBUS / VANY (jeśli body_style potwierdza wariant osobowy/przeszklony). Jeśli ilość miejsc <= 3 i typ nadwozia to furgon → preferuj klasy dostawcze.

WAŻNE: Musisz ocenić WSZYSTKIE {len(unique_classes)} klas. Klasy, do których pojazd absolutnie nie pasuje, powinny dostać confidence bliskie 0.0.
Posortuj wyniki od najwyższego do najniższego confidence.
"""

    try:
        gemini = get_gemini_client()
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
                response_schema={
                    "type": "object",
                    "properties": {
                        "candidates": {
                            "type": "array",
                            "description": (
                                "Wszystkie klasy SAMAR posortowane "
                                "od najwyższego confidence."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "klasa": {
                                        "type": "string",
                                        "description": "Nazwa klasy SAMAR.",
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "description": "Pewność 0.0-1.0.",
                                    },
                                },
                                "required": ["klasa", "confidence"],
                            },
                        },
                    },
                    "required": ["candidates"],
                },
            ),
        )

        resp_text = getattr(response, "text", "{}") or "{}"
        result = json.loads(resp_text)
        candidates = result.get("candidates", [])

        # Sort by confidence descending (safety net)
        candidates.sort(key=lambda c: c.get("confidence", 0), reverse=True)

        # Filter out zero-confidence noise
        candidates = [c for c in candidates if c.get("confidence", 0) > 0.01]

        if candidates:
            best = candidates[0]
            best_class = best["klasa"].strip()
            code = _extract_short_code(best_class)
            return (code, best_class, candidates)

    except Exception as exc:
        logger.exception("[SAMAR MAPPER] Gemini error: %s", exc)

    return fallback


def _extract_short_code(class_name: str) -> str:
    """Extract a short segment code from a full SAMAR class name.

    Examples
    --------
    >>> _extract_short_code("PODSTAWOWA D ŚREDNIA")
    'D'
    >>> _extract_short_code("TERENOWO-REKREACYJNE C NIŻSZA ŚREDNIA")
    'Csuv'
    >>> _extract_short_code("VANY C MINIVANY")
    'Cvan'
    """
    name_lower = class_name.lower()

    # Detect category prefix
    is_suv = "terenowo" in name_lower
    is_sport = "sportowo" in name_lower
    is_van = "vany" in name_lower or "minivan" in name_lower or "kombi" in name_lower
    is_dostawcze = "dostawcze" in name_lower
    is_minibus = "minibus" in name_lower
    is_pickup = "pick-up" in name_lower

    # Detect segment letter
    segment = ""
    for letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
        if f" {letter} " in class_name:
            segment = letter
            break

    if not segment:
        if "luksus" in name_lower:
            segment = "F"
        elif "mini" in name_lower and not is_minibus:
            segment = "A"

    # Build compound code
    if is_suv:
        return f"{segment}suv"
    if is_sport:
        return f"{segment}sport"
    if is_van:
        return f"{segment}van"
    if is_dostawcze:
        return "DOSTx"
    if is_minibus:
        return "MINIBUS"
    if is_pickup:
        return "PICKUP"

    return segment or "UNKNOWN"
