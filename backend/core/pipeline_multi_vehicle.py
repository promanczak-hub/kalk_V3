"""
Phase 0: Multi-vehicle detection and splitting.

Uses Gemini Flash to determine if a document contains multiple
vehicles. If so, uses Gemini Pro to extract N separate digital twins.
If only 1 vehicle, returns early and lets the standard pipeline handle it.

Deterministic fallback (2026-05-19): when Flash says 1 vehicle but the
extracted PDF text contains ≥2 separate "Kalkulacja dla / Cena specjalna /
Konfiguracja nr" sections, override Flash's count to the section count.
This catches the same-model-multi-variant case (2× Hilux, 2× Master) where
Flash misclassifies the offer as a "general price list with engine versions".
"""

import json
import logging
import re
from typing import Union

from google.genai import types

from core.gemini_client import (
    get_gemini_client,
    SAFETY_SETTINGS_PERMISSIVE,
    generate_content_with_retry,
    resolve_max_output_tokens,
)
from core.json_utils import clean_json_response
from core.prompts import MULTI_VEHICLE_DETECTION_PROMPT

logger = logging.getLogger(__name__)

# Polish word-to-number mapping for Flash responses
_WORD_TO_NUM: dict[str, int] = {
    "jeden": 1,
    "dwa": 2,
    "trzy": 3,
    "cztery": 4,
    "pięć": 5,
    "sześć": 6,
    "siedem": 7,
    "osiem": 8,
    "dziewięć": 9,
    "dziesięć": 10,
}


def _build_document_parts(
    document_data: Union[str, bytes],
    mime_type: str,
) -> list[types.Part]:
    """Convert raw document bytes/text into Gemini-compatible parts."""
    if isinstance(document_data, bytes):
        return [types.Part.from_bytes(data=document_data, mime_type=mime_type)]
    return [types.Part.from_text(text=document_data)]


def detect_vehicle_count(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
) -> int:
    """
    Lightweight Phase-0 probe using Gemini Flash.

    Returns the number of separate vehicle offers detected in the document.
    Falls back to 1 on any error.
    """
    client = get_gemini_client()
    doc_parts = _build_document_parts(document_data, mime_type)

    detection_prompt = types.Part.from_text(
        text=(
            "\n\n---\n"
            "INSTRUKCJA: Powyżej znajduje się zawartość dokumentu (oferta na pojazdy).\n"
            "Policz ile RÓŻNYCH pojazdów (różnych modeli/konfiguracji) "
            "jest opisanych w tym dokumencie.\n\n"
            "═══════════════════════════════════════════════\n"
            "REGUŁA NADRZĘDNA — SEKCJE KALKULACYJNE WYGRYWAJĄ\n"
            "═══════════════════════════════════════════════\n"
            "Jeśli dokument zawiera N OSOBNYCH sekcji z dowolną z poniższych fraz "
            "(traktuj je jako wyznaczniki indywidualnej kalkulacji):\n"
            "  • 'Kalkulacja dla Państwa firmy' / 'Kalkulacja dla [klient]'\n"
            "  • 'Cena specjalna' / 'Cena całkowita'\n"
            "  • 'Konfiguracja nr X' / 'Oferta nr X'\n"
            "  • 'Wybrane wyposażenie dodatkowe' (z własną kwotą)\n"
            "→ to N OSOBNYCH POJAZDÓW, NIEZALEŻNIE od tego czy to ten sam model.\n"
            "Ta reguła ma PIERWSZEŃSTWO przed jakimkolwiek 'wyjątkiem cennika ogólnego'.\n\n"
            "Przykład krytyczny (do nauczenia):\n"
            "  PDF z 2× Toyota Hilux (Executive 2.4 D-4D + Comfort 2.8 D-4D),\n"
            "  każdy z własną 'Kalkulacja dla Państwa firmy' i 'Cena specjalna'\n"
            "  → ZAWSZE 2, nigdy 1. To NIE jest 'cennik ogólny'.\n\n"
            "═══════════════════════════════════════════════\n"
            "POZOSTAŁE ZASADY (gdy reguła nadrzędna nie rozstrzyga)\n"
            "═══════════════════════════════════════════════\n"
            "- Każdy ODRĘBNY model pojazdu = 1 osobny pojazd.\n"
            "- Różne modele od TEGO SAMEGO producenta to OSOBNE pojazdy! "
            "Przykład: Lexus ES + Lexus RX + Lexus NX = 3 pojazdy.\n"
            "- Różne marki w jednym dokumencie = osobne pojazdy. "
            "Przykład: Toyota Corolla + Lexus NX = 2 pojazdy.\n"
            "- W arkuszu Excel (XLSX) każdy arkusz/zakładka z osobnym pojazdem "
            "= 1 pojazd (arkusz 'Podsumowanie'/'Summary' NIE jest osobnym pojazdem).\n"
            "- W pliku PDF szukaj osobnych sekcji cenowych, osobnych tabel specyfikacji, "
            "osobnych kodów konfiguracji lub osobnych numerów ofert — "
            "każda taka sekcja = 1 pojazd.\n"
            "- WYJĄTEK 'cennik ogólny': stosuj TYLKO gdy WSZYSTKIE wersje silnikowe "
            "jednego modelu (np. Skoda Octavia 1.0 TSI / 1.5 TSI / 2.0 TDI) są "
            "wymienione w JEDNEJ wspólnej tabeli i BRAK jest osobnych sekcji "
            "'Kalkulacja dla...' / 'Cena specjalna' per wersja. Jeśli choć jedna "
            "z tych fraz pojawia się więcej niż raz → reguła nadrzędna wygrywa.\n"
            "- Różne GENERACJE / ROCZNIKI tego samego modelu (np. 'MY24' vs 'NG 26', "
            "'pre-FL' vs 'FL', 'I' vs 'II' generacja, 'Hilux MY24' vs 'Hilux NG 26') "
            "= OSOBNE pojazdy, nawet jeśli mają tę samą nazwę modelu.\n\n"
            "PRZYKŁADY (dla wzmocnienia reguły nadrzędnej):\n"
            "- PDF z 2× Toyota Hilux (różne trim/silnik), każdy z osobną 'Kalkulacja dla' → 2\n"
            "- PDF z 2× Renault Master (Furgon L2H2 + L3H3), każdy z osobną 'Cena specjalna' → 2\n"
            "- PDF z ofertą na Lexus ES 300h, Lexus RX 450h i Lexus NX 350h → 3\n"
            "- PDF z ofertą na Renault Trafic, Kangoo Van, Master → 3\n"
            "- XLSX z 9 arkuszami, każdy z innym Renault → 9\n"
            "- PDF cennik Skoda Octavia z 4 wersjami silnika w JEDNEJ tabeli, "
            "BEZ powtórzonych 'Kalkulacja dla' / 'Cena specjalna' → 1\n"
            "- PDF z Toyota Yaris + Lexus UX → 2\n"
            "- PDF 'Toyota Business' z Hilux MY24 (Executive) + Hilux NG '26 (LIVE), "
            "każdy z osobną sekcją 'Kalkulacja dla Państwa firmy' i własną "
            "'Cena specjalna' → 2\n\n"
            "ODPOWIEDZ WYŁĄCZNIE jedną liczbą całkowitą. "
            "Nic więcej, żadnych wyjaśnień.\n"
            "ODPOWIEDŹ:"
        )
    )

    # Send document + prompt together as contents
    contents = doc_parts + [detection_prompt]

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=16,
        response_mime_type="text/plain",
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )
        raw_text = (getattr(response, "text", "1") or "1").strip()
        logger.info("[MULTI-VEHICLE] Raw Flash response: '%s'", raw_text)
        # Extract first number if Flash adds extra text
        digits = (
            "".join(c for c in raw_text.split()[0] if c.isdigit()) if raw_text else "1"
        )
        if digits:
            count = int(digits)
        else:
            # Fallback: try Polish word-to-number
            first_word = raw_text.split()[0].lower() if raw_text else ""
            count = _WORD_TO_NUM.get(first_word, 1)
            if count > 1:
                logger.info(
                    "[MULTI-VEHICLE] Parsed word '%s' as %d",
                    first_word,
                    count,
                )
        logger.info("[MULTI-VEHICLE] Gemini Flash detected %d vehicle(s)", count)
        return max(count, 1)
    except (ValueError, TypeError) as e:
        logger.warning(
            "[MULTI-VEHICLE] Could not parse vehicle count, defaulting to 1: %s", e
        )
        return 1
    except Exception as e:
        logger.warning("[MULTI-VEHICLE] Detection error, defaulting to 1: %s", e)
        return 1


def extract_multi_vehicle_twins(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
    expected_count: int = 2,
    text_data: str | None = None,
) -> list[dict]:
    """
    Full multi-vehicle extraction using Gemini Pro.

    Sends the document with `MULTI_VEHICLE_DETECTION_PROMPT`
    which instructs Gemini to return N separate digital twins.

    Returns a list of dicts, each containing:
      - brand, model, offer_number, configuration_code, digital_twin
    """
    client = get_gemini_client()
    contents = _build_document_parts(document_data, mime_type)

    if text_data:
        contents.append(
            types.Part.from_text(
                text=f"--- EXTRACTED TEXT (MARKDOWN) ---\n{text_data}\n--- END EXTRACTED TEXT ---\n\nThe original document is attached below. Use BOTH the markdown text and the visual document to extract all features, dimensions, weights, and packages. Pay special attention to visual diagrams with measurements."
            )
        )

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=resolve_max_output_tokens(),
        response_mime_type="application/json",
        system_instruction=MULTI_VEHICLE_DETECTION_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        thinking_config=types.ThinkingConfig(
            thinking_budget=16384,
        ),
    )

    try:
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-pro",
            contents=contents,
            config=config,
        )
        raw_text = getattr(response, "text", "{}") or "{}"
        data = json.loads(clean_json_response(raw_text))

        vehicles = data.get("vehicles", [])
        if not isinstance(vehicles, list) or len(vehicles) == 0:
            logger.warning(
                "[MULTI-VEHICLE] Pro returned no vehicles array, falling back"
            )
            return []

        logger.info(
            "[MULTI-VEHICLE] Gemini Pro extracted %d vehicle twin(s)", len(vehicles)
        )
        return vehicles

    except json.JSONDecodeError as e:
        logger.warning("[MULTI-VEHICLE] JSON decode error from Pro: %s", e)
        return []
    except Exception as e:
        logger.warning("[MULTI-VEHICLE] Extraction error: %s", e)
        return []


# ── Deterministic fallback: count "Kalkulacja dla / Cena specjalna / ..." sections ──
#
# These phrases anchor a per-vehicle calculation block in Polish B2B offer PDFs.
# When Flash misclassifies a same-model multi-variant offer as a "price list",
# counting these anchor phrases in the raw PDF text recovers the correct N.
#
# Pattern design rules:
# - Each pattern matches ONE-per-vehicle phrases (e.g. "Cena specjalna" appears
#   exactly once per offer block).
# - Case-insensitive (Polish capitalization varies between vendors).
# - Polish diacritics are part of the match (no folding — these phrases use
#   ASCII letters or stable diacritics).
_CALCULATION_SECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bKalkulacja\s+dla\b", re.IGNORECASE),
    re.compile(r"\bCena\s+specjalna\b", re.IGNORECASE),
    re.compile(r"\bKonfiguracja\s+nr\b", re.IGNORECASE),
    re.compile(r"\bOferta\s+nr\b", re.IGNORECASE),
    re.compile(r"\bWybrane\s+wyposa[zż]enie\s+dodatkowe\b", re.IGNORECASE),
)


def count_calculation_sections(text: str | None) -> int:
    """Count distinct per-vehicle calculation blocks in extracted PDF text.

    Returns the MAX count across all anchor patterns — different vendors emit
    different combinations of phrases, but each pattern's count is a lower
    bound on the number of vehicles.

    Returns 0 for empty/None input.
    """
    if not text:
        return 0
    return max(
        (len(pattern.findall(text)) for pattern in _CALCULATION_SECTION_PATTERNS),
        default=0,
    )


def detect_and_split_vehicles(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
    text_data: str | None = None,
) -> list[dict] | None:
    """
    Main entry point for Phase 0.

    Returns:
      - None if document has exactly 1 vehicle (caller should use standard pipeline)
      - list[dict] with N vehicle dicts if N > 1

    Multi-source detection (Flash + deterministic heuristic):
      - Gemini Flash gives a count based on document semantics.
      - Regex counter (`count_calculation_sections`) gives a count based on
        anchor phrases in raw PDF text.
      - We use MAX(flash, heuristic). Flash > heuristic when Flash is right,
        heuristic catches Flash false-negatives on same-model multi-variant.
    """
    count = detect_vehicle_count(document_data, mime_type)

    # Deterministic fallback: if Flash says 1, check the text for separate
    # calculation sections. This catches "2× Hilux in one PDF" cases where
    # Flash mistakes the same-model offer for a general price list.
    section_count = count_calculation_sections(text_data)
    if section_count >= 2 and section_count > count:
        logger.warning(
            "[MULTI-VEHICLE] Flash returned %d but found %d calculation sections "
            "in PDF text — overriding to %d",
            count, section_count, section_count,
        )
        count = section_count

    if count <= 1:
        return None

    logger.info(
        "[MULTI-VEHICLE] Flash detected %d vehicles, sending to Pro for extraction...",
        count,
    )
    vehicles = extract_multi_vehicle_twins(
        document_data, mime_type, expected_count=count, text_data=text_data
    )

    if len(vehicles) < 2:
        # Retry once — Pro sometimes needs a stronger hint
        logger.info(
            "[MULTI-VEHICLE] Pro returned %d twin(s) (expected %d), retrying...",
            len(vehicles),
            count,
        )
        vehicles = extract_multi_vehicle_twins(
            document_data, mime_type, expected_count=count
        )

    if len(vehicles) < 2:
        logger.warning(
            "[MULTI-VEHICLE] Pro could not extract multiple twins "
            "after retry (got %d), fallback to single",
            len(vehicles),
        )
        return None

    if len(vehicles) != count:
        logger.warning(
            "[MULTI-VEHICLE] Count mismatch: Flash=%d vs Pro=%d",
            count,
            len(vehicles),
        )

    logger.info(
        "[MULTI-VEHICLE] Successfully extracted %d vehicles (Flash expected %d)",
        len(vehicles),
        count,
    )
    return vehicles
