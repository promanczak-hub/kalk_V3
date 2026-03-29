"""DB fetch functions for LTR sub-calculators.

All lookups use @redis_cache with TTL for automatic refresh after
admin updates rates tables without server restart.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, cast

from core.redis_cache import redis_cache

logger = logging.getLogger(__name__)


@redis_cache(ttl_seconds=1800, prefix="ltr_fetchers:")
def get_insurance_rates_from_db(samar_class_id: str) -> List[Dict[str, Any]]:
    """Pobiera tabelę ubezpieczeń dla danej klasy SAMAR (28 klas, 7 lat)."""
    from core.database import supabase

    try:
        if samar_class_id:
            res = (
                supabase.table("ltr_admin_ubezpieczenia")
                .select("*")
                .eq("klasa_samar_fk", samar_class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(List[Dict[str, Any]], res.data)
    except Exception as e:
        logger.warning("Error fetching insurance rates: %s", e)
    return []


@redis_cache(ttl_seconds=1800, prefix="ltr_fetchers:")
def get_replacement_car_rate_from_db(samar_class_id: str) -> Dict[str, Any]:
    """Pobiera parametry auta zastępczego z tabeli replacement_car_rates."""
    from core.database import supabase

    try:
        if samar_class_id:
            res = (
                supabase.table("replacement_car_rates")
                .select("*")
                .eq("klasa_samar_fk", samar_class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])
        # Brak danych dla tej klasy — zwróć pusty dict (koszt = 0)
    except Exception as e:
        logger.warning("Error fetching replacement car rate: %s", e)
    return {}


@redis_cache(ttl_seconds=1800, prefix="ltr_fetchers:")
def get_damage_coefficients_from_db(samar_class_id: str) -> Dict[str, Any]:
    """Pobiera współczynniki szkodowe dla klasy pojazdu."""
    from core.database import supabase

    try:
        if samar_class_id:
            res = (
                supabase.table("ltr_admin_wspolczynniki_szkodowe")
                .select("*")
                .eq("samar_class_id", samar_class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])
    except Exception as e:
        logger.warning("Error fetching damage coefficients: %s", e)
    return {}


@redis_cache(ttl_seconds=3600, prefix="ltr_fetchers:")
def get_vehicle_from_db(vid: str) -> Dict[str, Any]:
    """Pobiera dane pojazdu z vehicle_synthesis i mapuje na format kalkulatora."""
    if not vid:
        return {}

    from core.database import supabase
    from core.ltr_vehicle_resolvers import (
        _infer_zabudowa_type_id,
        _resolve_body_type_id_from_name,
        _resolve_engine_type_id,
        _resolve_samar_class_id_from_name,
    )

    try:
        res = (
            supabase.table("vehicle_synthesis")
            .select("id, brand, model, synthesis_data, zabudowa_apr_wr")
            .eq("id", vid)
            .execute()
        )
        if not res.data or not isinstance(res.data, list) or len(res.data) == 0:
            return {}

        row = res.data[0]
        sd = row.get("synthesis_data") or {}
        cs = sd.get("card_summary") or {}
        mai = sd.get("mapped_ai_data") or {}

        samar_category = str(
            cs.get("samar_category") or mai.get("samar_category") or ""
        )
        samar_class_id = _resolve_samar_class_id_from_name(samar_category)

        engine_category = str(
            cs.get("engine_category", "") or mai.get("fuel", "") or ""
        )
        engine_type_id = _resolve_engine_type_id(engine_category)

        body_type_name = str(mai.get("body_type") or cs.get("body_style") or "")
        body_type_id = cs.get("body_type_id") or _resolve_body_type_id_from_name(
            body_type_name
        )

        zabudowa_type_id = (
            sd.get("zabudowa_type_id")
            or cs.get("zabudowa_type_id")
            or mai.get("zabudowa_type_id")
        )
        if zabudowa_type_id in (None, ""):
            zabudowa_type_id = _infer_zabudowa_type_id(sd, body_type_name)
        if zabudowa_type_id not in (None, ""):
            try:
                zabudowa_type_id = int(zabudowa_type_id)
            except Exception:
                zabudowa_type_id = None

        power_kw_raw = cs.get("power_kw") or 0
        if not power_kw_raw:
            import re

            powertrain = cs.get("powertrain", "") or ""
            kw_match = re.search(r"(\d+)\s*kW", powertrain, re.IGNORECASE)
            if kw_match:
                power_kw_raw = int(kw_match.group(1))
            else:
                km_match = re.search(r"(\d+)\s*KM", powertrain, re.IGNORECASE)
                if km_match:
                    power_km = int(km_match.group(1))
                    power_kw_raw = round(power_km / 1.36)

        if not power_kw_raw or float(power_kw_raw) <= 0:
            raise ValueError(
                f"Nie udało się ustalić mocy pojazdu (brak kW i KM) dla ID: {vid}. "
                "Uzupełnij dane w panelu."
            )

        vehicle_dict: Dict[str, Any] = {
            "id": vid,
            "brand": row.get("brand", ""),
            "model": row.get("model", ""),
            "Segment": samar_category,
            "samar_class_id": int(samar_class_id),
            "engine_type_id": engine_type_id,
            "power_kw": float(power_kw_raw),
            "paint_type_id": cs.get("paint_type_id"),
            "body_type_id": body_type_id,
            "body_type_name": body_type_name,
            "drive_type": mai.get("drive_type") or cs.get("drive_type") or "",
            "zabudowa_apr_wr": bool(
                row.get("zabudowa_apr_wr", False) or zabudowa_type_id
            ),
            "zabudowa_type_id": zabudowa_type_id,
            "is_metalic": cs.get("is_metalic_paint", True),
            "rocznik": cs.get("rocznik", "current"),
        }
        return vehicle_dict

    except Exception as exc:
        raise ValueError(
            f"Błąd bazy danych podczas pobierania pojazdu (ID: {vid}): {exc}. "
            "Przerwanie procesu (Fail-Fast)."
        ) from exc
