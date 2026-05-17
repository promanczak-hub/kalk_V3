"""Normalizes vehicle model / trim / body_style fields.

Vehicle data extracted by LLM often pollutes the model field with brand
prefix, trim level, body type, engine specs, year codes, etc. This module
strips those out and re-distributes them to the proper columns.

The single entry point is `normalize_model_trim_body(...)`. It returns a
3-tuple `(model, trim, body)` where each may be None.

SOT body types come from `public.body_types` (32 rows, edytowalne w
Supabase Dashboard Table Editor). `get_sot_body_types()` jest lazy + lru_cache'owane;
po edycji w UI wywołaj `POST /api/admin/invalidate-cache` (clear lru) —
albo skonfiguruj Supabase Database Webhook żeby wywoływał ten endpoint automatycznie.
Constant `SOT_BODY_TYPES_FALLBACK` zostaje na wypadek gdy DB niedostępne
(import-time, testy bez Supabase).
"""

from __future__ import annotations

import functools
import logging
import re
import unicodedata
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# Fallback 32 SOT body types — używane gdy DB niedostępne (import-time,
# testy). Single-source-of-truth jest w `public.body_types`. Snapshot z
# 2026-04-29.
SOT_BODY_TYPES_FALLBACK: tuple[str, ...] = (
    "Hatchback", "Kombi", "Sedan", "SUV", "Liftback", "Coupe", "Cabrio",
    "Minivan", "5 drzwiowy", "4 drzwiowy",
    "Furgon", "Furgon brygadowy", "Pickup", "Van", "Podwozie",
    "Wieloosobowy", "Dwuosobowy", "5 drzwiowy VAN", "2 drzwiowy", "3 drzwiowy",
    "Kombi Dostawczy", "Podwozie Chłodnia", "Podwozie Izoterma",
    "Podwozie Skrzynia", "Podwozie Kontener", "Podwozie Wywrotka",
    "Podwozie Plandeka", "Furgon Chłodnia", "Podwozie Brygadowe Skrzynia",
    "Podwozie Brygadowe Kontener", "Podwozie Brygadowe Wywrotka",
    "Podwozie Brygadowe Plandeka",
)


@functools.lru_cache(maxsize=1)
def get_sot_body_types() -> tuple[str, ...]:
    """Lazy SOT body types z DB (`public.body_types.nazwa_nadwozia`).

    Cache'owane przez `lru_cache(maxsize=1)`. Po edycji w nakładce UI
    wywołaj `POST /api/admin/invalidate-cache`, który robi
    `get_sot_body_types.cache_clear()` — następne wywołanie pobiera świeże.

    Fallback do `SOT_BODY_TYPES_FALLBACK` gdy DB niedostępne (import-time
    issue, testy bez Supabase, transient outage).
    """
    try:
        from core.database import supabase  # local import — uniknięcie cyklu

        resp = (
            supabase.table("body_types")
            .select("nazwa_nadwozia")
            .execute()
        )
        rows = resp.data or []
        names = tuple(
            r["nazwa_nadwozia"]
            for r in rows
            if r.get("nazwa_nadwozia")
        )
        if not names:
            logger.warning(
                "get_sot_body_types: DB zwróciło 0 wierszy z body_types, "
                "fallback do SOT_BODY_TYPES_FALLBACK"
            )
            return SOT_BODY_TYPES_FALLBACK
        return names
    except Exception as exc:
        logger.warning(
            "get_sot_body_types: nie udało się pobrać body_types z DB (%s), "
            "fallback do SOT_BODY_TYPES_FALLBACK",
            exc,
        )
        return SOT_BODY_TYPES_FALLBACK


# Backwards-compat alias dla istniejących importów (np. test_model_normalizer).
# UWAGA: to jest fallback tuple, niekoniecznie aktualne. Nowy kod powinien
# wołać get_sot_body_types().
SOT_BODY_TYPES: tuple[str, ...] = SOT_BODY_TYPES_FALLBACK

# Producer body labels → canonical SOT body
BODY_ALIASES: dict[str, str] = {
    "avant": "Kombi",          # Audi
    "sportstourer": "Kombi",   # CUPRA / SEAT
    "limuzyna": "Sedan",       # BMW
    "variant": "Kombi",        # Volkswagen
    "touring": "Kombi",        # BMW (estate)
    "estate": "Kombi",
    "sportback": "Liftback",   # Audi (5-door coupé)
    "combi": "Kombi",          # Skoda spelling variant
    "stationwagon": "Kombi",
    "wagon": "Kombi",
    "saloon": "Sedan",
}

@functools.lru_cache(maxsize=1)
def _body_words_strippable() -> tuple[str, ...]:
    """Lazy union SOT body types ∪ BODY_ALIASES keys (do strip z model name).

    Cache invalidated wraz z `get_sot_body_types.cache_clear()`.
    """
    return tuple({*get_sot_body_types(), *BODY_ALIASES.keys()})

# Brand prefixes — common ones that LLM might prepend to model
KNOWN_BRAND_PREFIXES: tuple[str, ...] = (
    "Škoda", "Skoda", "Volkswagen", "Audi", "BMW", "Mercedes-Benz", "Mercedes",
    "Volvo", "Hyundai", "Kia", "Ford", "Renault", "Peugeot", "Citroën", "Citroen",
    "Opel", "Toyota", "Honda", "Mazda", "Nissan", "Tesla", "Cupra", "Seat",
    "Fiat", "Dacia", "Land Rover", "Jaguar", "Mini", "Porsche", "Lexus",
    "Subaru", "Mitsubishi", "Suzuki",
)

# Engine spec patterns (run from longest to shortest to avoid partial strips)
_ENGINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.?\s+\d+\s*(?:TFSI|TDI|TSI|HDI|CDI|MHEV|PHEV|HEV|eTSI|eTDI|eHybrid)\b.*$", re.IGNORECASE),
    # TFSI/TDI/TSI etc. without preceding digit (e.g. 'A5 Avant TFSI quattro')
    re.compile(r"\.?\s+(?:TFSI|TDI|TSI|HDI|CDI|MHEV|PHEV|HEV|eTSI|eTDI|eHybrid)\b.*$", re.IGNORECASE),
    re.compile(r"\.?\s+\d+(?:[\.,]\d+)?\s*(?:[lL]\b).*$"),  # 2.0L
    re.compile(r"\.?\s+\d+\s*kW\b.*$", re.IGNORECASE),
    re.compile(r"\.?\s+\(?\d+\s*KM\)?.*$"),
    re.compile(r"\.?\s+(?:S\s*tronic|S-tronic|DSG|CVT|xDrive|sDrive|quattro|4MATIC|4motion|AWD|FWD|RWD|PHEV|MHEV|HEV)\b.*$", re.IGNORECASE),
    # Body roof descriptors ('z wysokim dachem', 'z niskim dachem', 'L4H2')
    re.compile(r"\.?\s+(?:z\s+(?:wysokim|niskim|średnim|niższym|wyższym)\s+dachem)\b.*$", re.IGNORECASE),
    re.compile(r"\.?\s+L\d+H\d+\b.*$", re.IGNORECASE),
)

_YEAR_CODE_PATTERN = re.compile(r"\.?\s+(?:RM|MY|MR)\d{4}\b.*$", re.IGNORECASE)

# Common trim/version words used to strip when trim_level is null but model leaked them
_GENERIC_TRIM_WORDS: tuple[str, ...] = (
    "Sportline", "Drive", "Selection", "Essence", "Elegance", "Ambition",
    "Style", "Active", "Highline", "Trendline", "L&K", "Laurin", "RS",
    "R-Line", "M Sport", "M-Sport", "GTI", "GTD", "GT", "Exclusive", "Premium",
    "Business", "Comfort", "Edition", "Pro", "Plus", "Life", "Core", "S line",
    "Allstar", "AllStar", "Executive", "Expression", "ST-LINE", "WILDTRAK",
    "TREND", "Trend", "XLT", "XLS",
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_diacritics(s: str) -> str:
    """ASCII-fold for case-insensitive matching across diacritics ('Škoda' ↔ 'Skoda')."""
    return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8")


def _strip_brand_prefix(s: str, brand: Optional[str]) -> str:
    """Remove brand name (or aliases) from start of model string."""
    candidates: list[str] = list(KNOWN_BRAND_PREFIXES)
    if brand:
        candidates.insert(0, brand)
        candidates.insert(0, _strip_diacritics(brand))
    seen: set[str] = set()
    for prefix in candidates:
        if not prefix or prefix.lower() in seen:
            continue
        seen.add(prefix.lower())
        # Match prefix followed by space/dot, case-insensitive
        # Also handle ASCII-folded comparison
        pattern = re.compile(rf"^{re.escape(prefix)}[\.\s]+", re.IGNORECASE)
        new_s = pattern.sub("", s, count=1)
        if new_s != s:
            return new_s.strip()
        # Try with diacritics stripped on both sides
        ascii_s = _strip_diacritics(s)
        ascii_prefix = _strip_diacritics(prefix)
        ascii_pattern = re.compile(rf"^{re.escape(ascii_prefix)}[\.\s]+", re.IGNORECASE)
        m = ascii_pattern.match(ascii_s)
        if m:
            return s[m.end():].strip()
    return s


def _strip_engine_and_year(s: str) -> str:
    """Remove engine designations, kW, KM, gearbox names, year codes from string."""
    s = _YEAR_CODE_PATTERN.sub("", s)
    for pattern in _ENGINE_PATTERNS:
        s = pattern.sub("", s)
    return s.strip()


def _strip_body_words(s: str, current_body: Optional[str]) -> tuple[str, Optional[str]]:
    """Strip body type words from model. Returns (cleaned_string, derived_body).

    Iterates so that 'Octavia Combi Drive Essence' loses 'Combi' even when not
    at very end (after trim is also stripped). Records first body match for the
    derived body_style if none was provided.
    """
    derived = current_body
    changed = True
    while changed:
        changed = False
        for word in _body_words_strippable():
            # Match word as whole token, anywhere except very start (we want model name first)
            pattern = re.compile(rf"(?<=\S)\.?\s+{re.escape(word)}(?=\s|\.|$)", re.IGNORECASE)
            new_s = pattern.sub("", s)
            if new_s != s:
                if not derived:
                    canonical = BODY_ALIASES.get(word.lower(), word)
                    if canonical in get_sot_body_types():
                        derived = canonical
                s = new_s
                changed = True
                break
    return s.strip(), derived


def _strip_trim_suffix(s: str, trim: Optional[str]) -> tuple[str, Optional[str]]:
    """Remove trim from model. If model has more after trim, extend trim with the tail.

    Example: model='Passat Business Plus', trim='Business' → model='Passat', trim='Business Plus'
    """
    if not trim:
        return s, trim
    # Find trim at end (with possible additional words after)
    pattern = re.compile(rf"\b{re.escape(trim)}\b(.*)$", re.IGNORECASE)
    m = pattern.search(s)
    if not m:
        return s, trim
    tail = m.group(1).strip(" .")
    new_trim = trim
    if tail:
        # Extend trim with tail (e.g. "Business" + "Plus" → "Business Plus")
        new_trim = f"{trim} {tail}".strip()
    cut_at = m.start()
    new_s = s[:cut_at].rstrip(" .,;").strip()
    return new_s, new_trim


def _strip_generic_trim_words(s: str) -> str:
    """Strip well-known trim words from end of model when trim_level wasn't set."""
    changed = True
    while changed:
        changed = False
        for word in _GENERIC_TRIM_WORDS:
            pattern = re.compile(rf"\s+{re.escape(word)}\s*$", re.IGNORECASE)
            new_s = pattern.sub("", s)
            if new_s != s:
                s = new_s
                changed = True
                break
    return s


# Allowlist of abbreviations to preserve as UPPER in title-case
_PRESERVE_UPPER: frozenset[str] = frozenset({
    "RS", "GTI", "GTD", "GT", "AMG", "M", "S", "R", "L&K",
    "BMW", "VW", "AWD", "FWD", "RWD", "TFSI", "TDI", "TSI",
    # Mercedes-Benz model-letter codes
    "GLA", "GLB", "GLC", "GLE", "GLS", "GLK", "EQA", "EQB", "EQC", "EQE", "EQS", "EQV",
    # Other manufacturer abbreviations
    "ID", "RAV4", "CHR", "SUV", "WRX", "STI",
})


def _title_case_model(s: str) -> str:
    """Title-case model name preserving known abbreviations and digit-letter mixes.

    Rules:
    - Words in `_PRESERVE_UPPER` stay UPPER (RS, GTI, GT, AMG, ...).
    - Mixed-case words (e.g., 'iPace', 'eTron') are preserved as-is.
    - Numbers + letters stay as-is (320i, A6, X5, RS6).
    - Everything else: Title Case (first letter upper, rest lower).
    """
    if not s:
        return s

    def _word(w: str) -> str:
        if not w:
            return w
        # Whole word is a known abbreviation → keep upper
        if w.upper() in _PRESERVE_UPPER:
            return w.upper()
        # Preserve mixed-case (camelCase-ish: starts lower with upper after)
        if w != w.upper() and w != w.lower() and w[0].islower():
            return w
        # Words containing digits — preserve as-is (320i, A6, S3)
        if any(ch.isdigit() for ch in w):
            return w
        # Default: title case (handle alpha-only or words with non-alpha like "L&K" handled above)
        if not any(ch.isalpha() for ch in w):
            return w
        return w[:1].upper() + w[1:].lower()

    parts = re.split(r"(\s+)", s)
    return "".join(_word(p) if not p.isspace() else p for p in parts)


def _is_engine_only_trim(trim: str) -> bool:
    """Detect if trim_level is actually an engine/body descriptor (not a real trim)."""
    s = trim.strip()
    # Patterns: '45 TFSI quattro', '20 xDrive', '320i xDrive', '2.0 TDI'
    if re.match(r"^\d+(?:[\.,]\d+)?\s*(?:TFSI|TDI|TSI|HDI|CDI|MHEV|PHEV|kW|KM|i\b|d\b)\s*", s, re.IGNORECASE):
        return True
    if re.match(r"^\d+\s*(?:xDrive|sDrive|quattro|4MATIC)\b", s, re.IGNORECASE):
        return True
    # Body descriptors masquerading as trim ('Furgon z wysokim dachem', 'Kombi N1', 'Maxi Furgon L4H2')
    if re.match(r"^(?:Furgon|Maxi|Pickup|Kombi|Van|Podwozie)\b", s, re.IGNORECASE):
        return True
    if re.match(r".*\bL\d+H\d+\b", s, re.IGNORECASE):
        return True
    return False


def _canonicalize_body(body: Optional[str]) -> Optional[str]:
    """Map producer body labels (Avant, Sportstourer, Limuzyna) to SOT canonical."""
    if not body:
        return None
    s = body.strip()
    if not s:
        return None
    # Direct SOT match (case-insensitive against the canonical list)
    for sot in get_sot_body_types():
        if s.lower() == sot.lower():
            return sot
    # Alias match
    return BODY_ALIASES.get(s.lower(), s)


# ── Public API ───────────────────────────────────────────────────────────────

def normalize_trim(raw_trim: Optional[str]) -> Optional[str]:
    """Clean trim_level: 'Brak', '-', '', engine-only patterns → None. Otherwise trim whitespace."""
    if raw_trim is None:
        return None
    s = raw_trim.strip()
    if not s:
        return None
    if s.lower() in ("brak", "-", "n/a", "none", "null"):
        return None
    if _is_engine_only_trim(s):
        return None
    # Collapse whitespace
    return " ".join(s.split())


def normalize_model_trim_body(
    raw_model: Optional[str],
    brand: Optional[str] = None,
    raw_trim: Optional[str] = None,
    raw_body: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Decompose contaminated model field into (model, trim, body_style).

    Pipeline:
      1. Strip brand prefix (Škoda, Volkswagen, ...).
      2. Strip engine specs (TFSI, kW, KM, xDrive, S tronic) and year codes (RM2022).
      3. Replace dot separators with spaces.
      4. Strip body words (SOT + producer aliases). If `raw_body` is empty,
         derive it from the matched word.
      5. If `raw_trim` exists: locate it in model, strip it. If model has tail
         after trim, extend trim ('Business' + 'Plus' → 'Business Plus').
      6. Strip generic leftover trim words (Sportline, RS, etc.).
      7. Title-case the result.

    Returns (None, None, None) for fully empty input.
    """
    norm_trim = normalize_trim(raw_trim)
    norm_body = _canonicalize_body(raw_body)

    if not raw_model:
        return None, norm_trim, norm_body

    s = raw_model.strip()

    # Step 1: brand prefix
    s = _strip_brand_prefix(s, brand)
    # Step 2: engine and year
    s = _strip_engine_and_year(s)
    # Step 3: dot separators
    s = re.sub(r"\.\s*", " ", s)
    s = " ".join(s.split())
    # Step 4: body words
    s, norm_body = _strip_body_words(s, norm_body)
    # Step 5: trim suffix (may extend trim)
    s, norm_trim = _strip_trim_suffix(s, norm_trim)
    # Step 6: generic trim leftovers
    s = _strip_generic_trim_words(s)
    # Cleanup
    s = " ".join(s.split())
    # Step 7: title case
    s = _title_case_model(s)

    return (s or None), norm_trim, norm_body
