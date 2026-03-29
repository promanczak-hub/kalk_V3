"""Vehicle ID resolution functions for LTR Calculator.

Maps string names (engine category, SAMAR class, body type, zabudowa type,
paint type) to integer IDs used in the database.

All DB lookups use @redis_cache with TTL for automatic cache expiry when
admin updates reference data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.redis_cache import redis_cache

logger = logging.getLogger(__name__)


# ── Lookup helpers ──────────────────────────────────────────────────

_PL_CHARS_TRANSLATION = str.maketrans(
    {
        "\u0104": "A",
        "\u0106": "C",
        "\u0118": "E",
        "\u0141": "L",
        "\u0143": "N",
        "\u00d3": "O",
        "\u015a": "S",
        "\u0179": "Z",
        "\u017b": "Z",
    }
)

_ZABUDOWA_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "KONTENER": ("KONTENER", "BOX", "BOX BODY"),
    "IZOTERMA": ("IZOTERMA", "ISOTHERM"),
    "CHLODNIA": ("CHLODNIA", "CHLODNI", "CHILLER", "REEFER"),
    "SKRZYNIA": ("SKRZYNIA", "SKRZYNI", "DROPSIDE"),
    "PLANDEKA": ("PLANDEKA", "TARPAULIN"),
    "AUTOLAWETA": ("AUTOLAWETA", "LAWETA", "CAR CARRIER"),
    "PODWOZIE": ("PODWOZIE", "CHASSIS", "PLATFORM"),
}


def _norm_lookup_key(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .upper()
        .translate(_PL_CHARS_TRANSLATION)
        .replace("-", " ")
        .replace("_", " ")
    )


# ── Engine type ID resolution ───────────────────────────────────────


@redis_cache(ttl_seconds=3600, prefix="ltr_resolvers:")
def _get_engine_mapping() -> Dict[str, int]:
    """Pobiera i cache'uje mapowanie silników z bazy Supabase."""
    from core.database import supabase

    try:
        res = supabase.table("engines").select("id, name").execute()
        mapping: Dict[str, int] = {}
        for item in res.data:
            name_upper = str(item["name"]).upper()
            mapping[name_upper] = item["id"]
            # Dodajemy uproszczone aliasy z nawiasów (np. PB, ON, BEV)
            if "(" in name_upper and ")" in name_upper:
                alias = name_upper.split("(")[1].split(")")[0].strip()
                if alias:
                    mapping[alias] = item["id"]
        return mapping
    except Exception as e:
        logger.error("Error fetching engine mapping: %s", e)
        return {}


def _resolve_engine_type_id(engine_category: str) -> int:
    """Mapuje string kategorii silnika na engines.id."""
    if not engine_category:
        raise ValueError("Brak parametru engine_category.")

    upper = engine_category.strip().upper()
    mapping = _get_engine_mapping()

    # 1. Próba dopasowania całego stringu
    if upper in mapping:
        return mapping[upper]

    # 2. Logika heurystyczna dla skrótów i wariantów (V1 Parity)
    if "PHEV" in upper or "PLUG-IN" in upper:
        return 6
    if "MHEV" in upper and ("DIESEL" in upper or "ON" in upper):
        return 4
    if "MHEV" in upper and ("BENZYNA" in upper or "PB" in upper):
        return 3
    if "FCEV" in upper or "WODOR" in upper or "WODÓR" in upper:
        return 8
    if "HEV" in upper or "HYBRYDA" in upper:
        return 5
    if "ELEKTR" in upper or "BEV" in upper or upper == "EV":
        return 7
    if "LPG" in upper:
        return 9
    if "DIESEL" in upper or "ON" in upper:
        return 2
    if "BENZYNA" in upper or "PB" in upper:
        return 1

    # 3. Próba znalezienia klucza wewnątrz nazwy
    for name, eid in mapping.items():
        if name in upper:
            return eid

    raise ValueError(
        f"Nieznana kategoria silnika: '{engine_category}'. "
        "Brak mapowania na engine_type_id w bazie danych."
    )


# ── SAMAR class ID resolution ───────────────────────────────────────


@redis_cache(ttl_seconds=3600, prefix="ltr_resolvers:")
def _resolve_samar_class_id_from_name(samar_category: str) -> int:
    if not samar_category:
        return 0

    from core.database import supabase

    cls_res = supabase.table("samar_classes").select("id, name").execute()

    def _norm_samar(s: str) -> str:
        return s.strip().upper().replace("KLASA ", "").replace("SAMAR: ", "").strip()

    cat_norm = _norm_samar(samar_category)
    for cls_row in cls_res.data or []:
        db_name = str(cls_row.get("name", ""))
        if _norm_samar(db_name) == cat_norm:
            return int(cls_row["id"])
    return 0


# ── Body type ID resolution ─────────────────────────────────────────


@redis_cache(ttl_seconds=3600, prefix="ltr_resolvers:")
def _resolve_body_type_id_from_name(body_type_name: str) -> Optional[int]:
    if not body_type_name:
        return None
    try:
        from core.body_type_matcher import match_body_type

        match = match_body_type(body_type_name)
        return int(match.matched_body_type_id) if match.matched_body_type_id else None
    except Exception:
        return None


# ── Paint type ID resolution ────────────────────────────────────────


@redis_cache(ttl_seconds=3600, prefix="ltr_resolvers:")
def _resolve_paint_type_id_from_name(paint_type_name: str) -> Optional[int]:
    if not paint_type_name:
        return None
    from core.database import supabase

    try:
        norm = paint_type_name.strip().upper()
        res = supabase.table("paint_types").select("id, name").execute()
        for row in res.data or []:
            row_name = str(row.get("name", "")).strip().upper()
            if row_name == norm:
                return int(row["id"])
        for row in res.data or []:
            row_name = str(row.get("name", "")).strip().upper()
            if row_name and (row_name in norm or norm in row_name):
                return int(row["id"])
    except Exception:
        return None
    return None


# ── Zabudowa type ID resolution ─────────────────────────────────────


@redis_cache(ttl_seconds=3600, prefix="ltr_resolvers:")
def _load_zabudowa_types_map() -> Dict[str, int]:
    try:
        from core.database import supabase

        resp = supabase.table("body_types").select("id, name").execute()
        out: Dict[str, int] = {}
        for row in resp.data or []:
            name = str(row.get("name") or "").strip()
            if name:
                out[_norm_lookup_key(name)] = int(row["id"])
        return out
    except Exception as exc:
        logger.warning("Nie udało się załadować body_types jako zabudowa: %s", exc)
        return {}


def _resolve_zabudowa_type_id_from_name(zabudowa_name: str) -> Optional[int]:
    if not zabudowa_name:
        return None

    mapping = _load_zabudowa_types_map()
    if not mapping:
        return None

    normalized = _norm_lookup_key(zabudowa_name)
    if not normalized:
        return None

    if normalized in mapping:
        return mapping[normalized]

    for map_name, map_id in mapping.items():
        if map_name in normalized or normalized in map_name:
            return map_id

    detected_key: Optional[str] = None
    for canonical_key, keywords in _ZABUDOWA_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            detected_key = canonical_key
            break

    if detected_key:
        for map_name, map_id in mapping.items():
            if detected_key in map_name:
                return map_id

    return None


# ── Helper: infer zabudowa from synthesis_data ──────────────────────


def _extract_service_option_names(sd: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    cs = sd.get("card_summary") or {}

    paid_options = cs.get("paid_options") or []
    if isinstance(paid_options, list):
        for row in paid_options:
            if not isinstance(row, dict):
                continue
            category = str(row.get("category") or "").lower()
            if "fabryczna" in category:
                continue
            name = str(row.get("name") or "").strip()
            if name:
                names.append(name)

    service_options = sd.get("service_options") or []
    if isinstance(service_options, list):
        for row in service_options:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if name:
                names.append(name)
            components = row.get("description_or_components") or []
            if isinstance(components, list):
                for comp in components:
                    comp_name = str(comp or "").strip()
                    if comp_name:
                        names.append(comp_name)

    service_equipment = cs.get("service_equipment") or {}
    if isinstance(service_equipment, dict):
        main_name = str(service_equipment.get("name") or "").strip()
        if main_name:
            names.append(main_name)
        components = service_equipment.get("components") or []
        if isinstance(components, list):
            for comp in components:
                if not isinstance(comp, dict):
                    continue
                comp_name = str(comp.get("name") or "").strip()
                if comp_name:
                    names.append(comp_name)

    return names


def _infer_zabudowa_type_id(sd: Dict[str, Any], body_type_name: str = "") -> Optional[int]:
    candidates: List[str] = []
    if body_type_name:
        candidates.append(body_type_name)

    cs = sd.get("card_summary") or {}
    mai = sd.get("mapped_ai_data") or {}

    for source in (
        sd.get("zabudowa_type_name"),
        cs.get("zabudowa_type_name"),
        mai.get("zabudowa_type_name"),
        cs.get("body_style"),
        mai.get("body_type"),
    ):
        text = str(source or "").strip()
        if text:
            candidates.append(text)

    candidates.extend(_extract_service_option_names(sd))

    for candidate in candidates:
        resolved = _resolve_zabudowa_type_id_from_name(candidate)
        if resolved:
            return resolved
    return None
