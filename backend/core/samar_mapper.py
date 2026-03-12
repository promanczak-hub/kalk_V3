"""Dynamic SAMAR class mapper using samar_classes dictionary + Gemini Flash.

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
    url = os.environ.get("SUPABASE_URL", os.environ.get("VITE_SUPABASE_URL", ""))
    key = os.environ.get("SUPABASE_KEY", os.environ.get("VITE_SUPABASE_ANON_KEY", ""))
    return create_client(url, key)


def _fetch_samar_dictionary(client: Client) -> list[dict]:
    """Fetch SAMAR class dictionary from ``samar_classes`` (28 classes).

    Returns a list of dicts: ``[{"klasa": "Podstawowa - D ŚREDNIA", "modele": "BMW Serii 3, ..."}]``
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
        client.table("samar_classes")
        .select("name, example_models")
        .order("id")
        .execute()
    )
    rows: list[dict] = []
    for row in response.data:
        klasa = (row.get("name") or "").strip()
        modele = (row.get("example_models") or "").strip()
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
) -> Tuple[str, list[dict]]:
    """Dynamically classify a vehicle into SAMAR classes with reranking.

    Queries ``samar_classes`` for the full dictionary, then asks
    Gemini Flash to rank ALL classes by probability.

    Returns
    -------
    tuple[str, list[dict]]
        ``(best_class_name, ranked_candidates)``
        where ``ranked_candidates`` is a list of
        ``{"klasa": "...", "confidence": 0.95}`` sorted desc.
        Falls back to ``("INNE - WYMAGA RĘCZNEGO MAPOWANIA", [])``
        on error.
    """
    fallback: Tuple[str, list[dict]] = (
        "INNE - WYMAGA RĘCZNEGO MAPOWANIA",
        [],
    )

    if not brand and not model:
        return fallback

    try:
        sb_client = _build_samar_client()
        url_used = os.environ.get(
            "SUPABASE_URL", os.environ.get("VITE_SUPABASE_URL", "NOT SET")
        )
        print(f"[SAMAR MAPPER DEBUG] Supabase URL used: {url_used[:40]}...")
        samar_dict = _fetch_samar_dictionary(sb_client)
        print(f"[SAMAR MAPPER DEBUG] Fetched {len(samar_dict)} SAMAR classes from DB")
    except Exception as exc:
        print(
            f"[SAMAR MAPPER DEBUG] EXCEPTION during init/fetch: {type(exc).__name__}: {exc}"
        )
        logger.exception(
            "[SAMAR MAPPER] Error initializing or fetching samar dict: %s", exc
        )
        return fallback

    if not samar_dict:
        logger.warning("[SAMAR MAPPER] Samar dictionary is empty! Returning fallback.")
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
        print(f"[SAMAR MAPPER DEBUG] Calling Gemini for brand={brand}, model={model}")
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
        print(
            f"[SAMAR MAPPER DEBUG] Gemini raw response (first 300 chars): {resp_text[:300]}"
        )
        result = json.loads(resp_text)
        candidates = result.get("candidates", [])
        print(f"[SAMAR MAPPER DEBUG] Got {len(candidates)} candidates from Gemini")

        # Sort by confidence descending (safety net)
        candidates.sort(key=lambda c: c.get("confidence", 0), reverse=True)

        # Filter out zero-confidence noise
        candidates = [c for c in candidates if c.get("confidence", 0) > 0.01]
        print(
            f"[SAMAR MAPPER DEBUG] After filtering: {len(candidates)} candidates, top={candidates[0] if candidates else 'NONE'}"
        )

        if candidates:
            best = candidates[0]
            best_class = best["klasa"].strip()
            print(
                f"[SAMAR MAPPER DEBUG] BEST CLASS: {best_class} (confidence={best.get('confidence')})"
            )
            return (best_class, candidates)

    except Exception as exc:
        print(f"[SAMAR MAPPER DEBUG] GEMINI EXCEPTION: {type(exc).__name__}: {exc}")
        logger.exception("[SAMAR MAPPER] Gemini error: %s", exc)

    return fallback
