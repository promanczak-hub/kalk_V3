"""Endpoint GET /api/resolve-vehicle-ids — resolves SAMAR class name and engine name to numeric IDs.

Lightweight replacement for the full readiness-check pipeline.
Used by frontend's useVehicleParamPreview to obtain numeric IDs.
"""

import logging
import re
from typing import Any, Dict, Optional, cast

from fastapi import APIRouter, Query

from core.database import supabase
from core.samar_rv import get_samar_class_id

logger = logging.getLogger(__name__)
router = APIRouter()

_engine_name_cache: Optional[Dict[str, int]] = None


def _load_engine_name_map() -> Dict[str, int]:
    global _engine_name_cache
    if _engine_name_cache:
        return _engine_name_cache
    try:
        resp = supabase.table("engines").select("id, name").execute()
        data = cast(Any, resp.data) or []
        _engine_name_cache = {
            str(row["name"]).strip().upper(): int(row["id"]) for row in data
        }
    except Exception as exc:
        logger.warning("Nie udało się załadować tabeli engines: %s", exc)
        return {}
    return _engine_name_cache


def _resolve_engine_id(engine_name: str) -> Optional[int]:
    if not engine_name or not engine_name.strip():
        return None

    mapping = _load_engine_name_map()
    normalized = engine_name.strip().upper()

    # 1. Exact match (case-insensitive)
    if normalized in mapping:
        return mapping[normalized]

    # 2. Partial match
    for key, fid in mapping.items():
        if key in normalized or normalized in key:
            return fid

    # 3. Fallback: tag in parentheses, e.g. (PB), (ON), (PHEV)
    match = re.search(r"\(([A-Z0-9\-]+)\)", normalized)
    if match:
        tag = f"({match.group(1)})"
        for key, fid in mapping.items():
            if tag in key:
                return fid

    # 4. Retry after cache reload
    if not mapping:
        global _engine_name_cache
        _engine_name_cache = None
        mapping = _load_engine_name_map()
        if normalized in mapping:
            return mapping[normalized]

    return None


@router.get("/resolve-vehicle-ids")
def resolve_vehicle_ids(
    samar_class_name: str = Query(default=""),
    engine_name: str = Query(default=""),
) -> Dict[str, Any]:
    """Resolve SAMAR class name and engine name to numeric DB IDs."""
    samar_class_id: Optional[int] = None
    fuel_type_id: Optional[int] = None

    if samar_class_name.strip():
        samar_class_id = get_samar_class_id(samar_class_name)

        # Fallback: try normalized lookup
        if samar_class_id is None:
            try:
                resp = supabase.table("samar_classes").select("id, name").execute()
                input_norm = (
                    samar_class_name.strip().upper().replace("KLASA ", "")
                )
                for row in resp.data or []:
                    db_norm = (
                        str(row.get("name", ""))
                        .strip()
                        .upper()
                        .replace("KLASA ", "")
                    )
                    if db_norm == input_norm:
                        samar_class_id = int(row["id"])
                        break
            except Exception as exc:
                logger.warning("Normalizacja SAMAR fallback error: %s", exc)

    if engine_name.strip():
        fuel_type_id = _resolve_engine_id(engine_name)

    return {
        "samar_class_id": samar_class_id,
        "fuel_type_id": fuel_type_id,
    }
