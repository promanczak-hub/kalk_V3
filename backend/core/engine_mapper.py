"""Dynamic engine class mapper using the 'engines' table + Gemini Flash.

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
_engine_cache: dict = {"data": None, "ts": 0.0}


def _build_engine_client() -> Client:
    """Create a lightweight Supabase client for engine lookups."""
    url = os.environ.get("VITE_SUPABASE_URL", "")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    return create_client(url, key)


def _fetch_engine_dictionary(client: Client) -> list[dict]:
    """Fetch engine dictionary rows from ``engines`` table.

    Uses in-memory cache with 5-minute TTL.
    """
    now = time.monotonic()
    if _engine_cache["data"] and (now - _engine_cache["ts"]) < _CACHE_TTL_SECONDS:
        logger.debug(
            "[ENGINE MAPPER] Using cached dictionary (%d rows)",
            len(_engine_cache["data"]),
        )
        return _engine_cache["data"]

    response = client.table("engines").select("name, category, description").execute()
    rows: list[dict] = []
    for row in response.data:
        name = (row.get("name") or "").strip()
        category = (row.get("category") or "").strip()
        description = (row.get("description") or "").strip()
        if name:
            rows.append(
                {"name": name, "category": category, "description": description}
            )

    _engine_cache["data"] = rows
    _engine_cache["ts"] = now
    logger.info("[ENGINE MAPPER] Refreshed cache: %d rows", len(rows))
    return rows


def map_to_engine_class(
    fuel: str | None = None,
    engine_designation: str | None = None,
    power: str | None = None,
    capacity: str | None = None,
    model: str | None = None,
    trim: str | None = None,
) -> Tuple[str, str, list[dict]]:
    """Dynamically classify an engine type with reranking.

    Queries ``engines`` for the full dictionary, then asks
    Gemini Flash to rank ALL classes by probability.

    Returns
    -------
    tuple[str, str, list[dict]]
        ``(best_name, best_category, ranked_candidates)``
        where ``ranked_candidates`` is a list of
        ``{"klasa": "...", "confidence": 0.95}`` sorted desc.
        Falls back to ``("UNKNOWN", "UNKNOWN", [])`` on error.
    """
    fallback: Tuple[str, str, list[dict]] = (
        "UNKNOWN",
        "UNKNOWN",
        [],
    )

    if not fuel and not engine_designation and not power and not capacity:
        return fallback

    try:
        sb_client = _build_engine_client()
        engine_dict = _fetch_engine_dictionary(sb_client)
    except Exception as e:
        logger.info("[ENGINE MAPPER] Supabase error: %s", e)
        return fallback

    if not engine_dict:
        return fallback

    # Unique engine classifications
    unique_names = list(dict.fromkeys(row["name"] for row in engine_dict))

    # Build a compact representation for the prompt
    dict_text = "\n".join(
        f"- {row['name']} ({row['category']}): {row['description']}"
        for row in engine_dict
    )

    prompt = f"""Jesteś ekspertem motoryzacyjnym. Twoim zadaniem jest klasyfikacja układu napędowego.

Oto PEŁNY słownik typów układów napędowych:
{dict_text}

Dane wyekstrahowane z dokumentu dla tego pojazdu:
- Odczytane Paliwo/Zasilanie: {fuel or "brak danych"}
- Oznaczenie technologii silnika (np. TSI, TDI, e-Hybrid): {engine_designation or "brak danych"}
- Model: {model or "brak danych"}
- Wersja/Trim: {trim or "brak danych"}
- Moc: {power or "brak danych"}
- Pojemność: {capacity or "brak danych"}

ZADANIE: Oceń prawdopodobieństwo przynależności tego pojazdu do KAŻDEGO opisanego typu napędu z powyższego słownika.
Dla KAŻDEGO napędu z listy przypisz confidence (0.0-1.0) — jak bardzo ten układ pasuje.

KRYTYCZNE WSKAZÓWKI:
1. Odczytane Paliwo (np. Benzyna, Diesel) to główny klucz, ale szukaj też słów mHEV, Mild Hybrid, miękka hybryda w oznaczeniu technologii lub trimie. Zwykła Benzyna to "Benzyna (PB)", a benzyna + mHEV to "Benzyna mHEV (PB-mHEV)".
2. Zwróć uwagę na Plug-In Hybrid (PHEV) (auto z wtyczką, zazwyczaj wyższa moc systemowa i dopisek e-Hybrid, TFSIe, PHEV).
3. Klasyczna Hybryda HEV nie ma wtyczki (Toyota Hybrid, Renault E-Tech pełen).
4. Jeśli widzisz tylko "Benzyna" i brak jakichkolwiek dopisków hybrydowych, to najprawdopodobniej czyste ICE.
5. "Elektryczny (BEV)" stosuj tylko dla pełnych elektryków (np. moc w kW bez uwag o silniku spalinowym).

WAŻNE: Musisz ocenić WSZYSTKIE {len(unique_names)} klas, używając DOKŁADNIE nazwy pola 'name' (np. "Benzyna (PB)", "Diesel mHEV (ON-mHEV)"). Klasy, do których to absolutnie nie pasuje, powinny dostać confidence bliskie 0.0.
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
                                "Wszystkie typy napędu posortowane "
                                "od najwyższego confidence."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "klasa": {
                                        "type": "string",
                                        "description": "Nazwa napędu z listy (name).",
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

        # Sort by confidence descending
        candidates.sort(key=lambda c: c.get("confidence", 0), reverse=True)

        # Filter out zero-confidence noise
        candidates = [c for c in candidates if c.get("confidence", 0) > 0.01]

        if candidates:
            best = candidates[0]
            best_name = best["klasa"].strip()
            # find category matching the best name
            best_category = "UNKNOWN"
            for row in engine_dict:
                if row["name"] == best_name:
                    best_category = row["category"]
                    break

            return (best_name, best_category, candidates)

    except Exception as exc:
        logger.exception("[ENGINE MAPPER] Gemini error: %s", exc)

    return fallback
