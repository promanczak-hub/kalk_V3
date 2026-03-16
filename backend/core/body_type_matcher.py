"""Fuzzy matching helper for body style normalization.

Resolves free-text body names into canonical body_types rows used by calculation
pipeline, while allowing selected user-facing aliases (e.g. "Kontener") to remain
visible in UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.database import supabase

logger = logging.getLogger(__name__)

# Maps common variants to canonical body_types.name.
# Keys must be upper-cased.
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

# For those aliases we keep the original label in UI, but still resolve to
# canonical ID for pipeline internals.
PRESERVE_RAW_ALIAS_KEYS: set[str] = set()


@dataclass
class BodyTypeMatch:
    """Result of fuzzy matching body_style -> body_types."""

    matched_body_type_id: Optional[int]
    matched_name: Optional[str]
    vehicle_class: Optional[str]
    score: int
    match_method: str  # exact | substring | alias | alias-preserve | none
    raw_input: str


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
    """Match raw body_style string to a body_types row."""
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

    # 1) Exact match
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

    # 2) Substring / contains
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

    # 3) Alias map
    canonical: Optional[str] = None
    preserve_raw_alias = False

    canonical = BODY_ALIAS_MAP.get(normalized)
    if canonical:
        preserve_raw_alias = normalized in PRESERVE_RAW_ALIAS_KEYS

    if not canonical:
        for alias_key, alias_val in BODY_ALIAS_MAP.items():
            if alias_key in normalized or normalized in alias_key:
                canonical = alias_val
                preserve_raw_alias = alias_key in PRESERVE_RAW_ALIAS_KEYS
                break

    if canonical:
        for bt in body_types:
            if bt["name"].strip().upper() == canonical.upper():
                matched_name = (
                    raw_body_style.strip() if preserve_raw_alias else bt["name"]
                )
                method = "alias-preserve" if preserve_raw_alias else "alias"
                return BodyTypeMatch(
                    matched_body_type_id=bt["id"],
                    matched_name=matched_name,
                    vehicle_class=bt["vehicle_class"],
                    score=85,
                    match_method=method,
                    raw_input=raw_body_style,
                )

    # 4) No match
    return BodyTypeMatch(
        matched_body_type_id=None,
        matched_name=None,
        vehicle_class=None,
        score=0,
        match_method="none",
        raw_input=raw_body_style,
    )



