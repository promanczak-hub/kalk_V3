"""Fuzzy matching: body_style (AI-extracted) → body_types table.

Multi-level matching with confidence score:
  1. Exact match → 100 %
  2. Substring / contains → 90 %
  3. Alias map (Touring→Kombi, Panel Van→Furgon…) → 85 %
  4. No match → score 0, result None

Returns BodyTypeMatch dataclass consumed by:
  - GET /api/match-body-type  (informational badge)
  - readiness-check            (body_type_id resolution)
  - body_type_wr_corrections   (WR cascade lookup)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.database import supabase

logger = logging.getLogger(__name__)

# ── Alias map ────────────────────────────────────────────────────────
# Maps common AI-extracted body names to canonical body_types.name.
# Keys MUST be UPPER-CASED.

BODY_ALIAS_MAP: dict[str, str] = {
    "TOURING": "Kombi",
    "AVANT": "Kombi",
    "WAGON": "Kombi",
    "ESTATE": "Kombi",
    "VARIANT": "Kombi",
    "SPORTSTOURER": "Kombi",
    "SPORTS TOURER": "Kombi",
    "SPORTSWAGON": "Kombi",
    "BREAK": "Kombi",
    "SW": "Kombi",
    "ALLTRACK": "Kombi",
    "CROSSOVER": "SUV",
    "CROSS": "SUV",
    "X-LINE": "SUV",
    "PANEL VAN": "Furgon",
    "CARGO": "Furgon",
    "CHŁODNIA": "Furgon",
    "SKRZYNIOWY": "Podwozie",
    "CHASSIS": "Podwozie",
    "DOSTAWCZY": "Furgon",
    "LIMOUSINE": "Sedan",
    "SALOON": "Sedan",
    "BERLINA": "Sedan",
    "SPORTBACK": "Liftback",
    "GRAN COUPE": "Liftback",
    "GRAN TURISMO": "Liftback",
    "FASTBACK": "Liftback",
    "CABRIOLET": "Cabrio",
    "CONVERTIBLE": "Cabrio",
    "ROADSTER": "Cabrio",
    "SPIDER": "Cabrio",
    "SPYDER": "Cabrio",
    "MPV": "Minivan",
    "MONOVOLUME": "Minivan",
    "MINIBUS": "Wieloosobowy",
    "BUS": "Wieloosobowy",
    "OSOBOWY BUS": "Wieloosobowy",
    "DOUBLE CAB": "Pickup",
    "SINGLE CAB": "Pickup",
    "CREW CAB": "Pickup",
}


@dataclass
class BodyTypeMatch:
    """Result of fuzzy matching body_style → body_types."""

    matched_body_type_id: Optional[int]
    matched_name: Optional[str]
    vehicle_class: Optional[str]  # "Osobowy" / "Dostawczy"
    score: int  # 0-100
    match_method: str  # "exact" | "substring" | "alias" | "none"
    raw_input: str


# ── Cache ────────────────────────────────────────────────────────────
_BODY_TYPES_CACHE: list[dict] | None = None


def _load_body_types() -> list[dict]:
    """Load body_types table (cached)."""
    global _BODY_TYPES_CACHE
    if _BODY_TYPES_CACHE is not None:
        return _BODY_TYPES_CACHE
    try:
        res = supabase.table("body_types").select("id, name, vehicle_class").execute()
        _BODY_TYPES_CACHE = res.data or []
    except Exception as exc:
        logger.warning("Failed to load body_types: %s", exc)
        _BODY_TYPES_CACHE = []
    return _BODY_TYPES_CACHE


def invalidate_cache() -> None:
    """Clear cached body_types (call after CRUD ops)."""
    global _BODY_TYPES_CACHE
    _BODY_TYPES_CACHE = None


def match_body_type(raw_body_style: str) -> BodyTypeMatch:
    """Match raw body_style string to a body_types row.

    Returns BodyTypeMatch with score and method.
    """
    if not raw_body_style or not raw_body_style.strip():
        return BodyTypeMatch(
            matched_body_type_id=None,
            matched_name=None,
            vehicle_class=None,
            score=0,
            match_method="none",
            raw_input=raw_body_style or "",
        )

    body_types = _load_body_types()
    normalized = raw_body_style.strip().upper()

    # 1. Exact match (case-insensitive)
    for bt in body_types:
        if bt["name"].strip().upper() == normalized:
            return BodyTypeMatch(
                matched_body_type_id=bt["id"],
                matched_name=bt["name"],
                vehicle_class=bt["vehicle_class"],
                score=100,
                match_method="exact",
                raw_input=raw_body_style,
            )

    # 2. Substring / contains match
    for bt in body_types:
        bt_upper = bt["name"].strip().upper()
        if bt_upper in normalized or normalized in bt_upper:
            return BodyTypeMatch(
                matched_body_type_id=bt["id"],
                matched_name=bt["name"],
                vehicle_class=bt["vehicle_class"],
                score=90,
                match_method="substring",
                raw_input=raw_body_style,
            )

    # 3. Alias map
    canonical = BODY_ALIAS_MAP.get(normalized)
    if not canonical:
        # Try partial alias match
        for alias_key, alias_val in BODY_ALIAS_MAP.items():
            if alias_key in normalized or normalized in alias_key:
                canonical = alias_val
                break

    if canonical:
        for bt in body_types:
            if bt["name"].strip().upper() == canonical.upper():
                return BodyTypeMatch(
                    matched_body_type_id=bt["id"],
                    matched_name=bt["name"],
                    vehicle_class=bt["vehicle_class"],
                    score=85,
                    match_method="alias",
                    raw_input=raw_body_style,
                )

    # 4. No match
    return BodyTypeMatch(
        matched_body_type_id=None,
        matched_name=None,
        vehicle_class=None,
        score=0,
        match_method="none",
        raw_input=raw_body_style,
    )
