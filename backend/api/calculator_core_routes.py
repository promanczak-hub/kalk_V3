import logging
from typing import Any, Dict, Optional, cast
from fastapi import APIRouter, HTTPException

from api.schemas.calculator import CalculatorInput
from core.database import supabase
from core.models import ControlCenterSettings

router = APIRouter()


@router.post("/calculate-matrix")
def calculate_matrix(data: CalculatorInput) -> Dict[str, Any]:
    try:
        from domain.calculations.service import CalculationService

        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )
        response_data = cast(Any, response.data[0])
        settings = ControlCenterSettings(**response_data)

        # Wykorzystanie wzorca UseCase/Service z domeny calculations
        calc_service = CalculationService(data=data, settings=settings)
        matrix_cells = calc_service.calculate_matrix()

        # Opcjonalny zrzut do konsoli, izolowany wewnątrz serwisu
        calc_service.print_terminal_trace(matrix_cells)

        return {
            "status": "success",
            "message": "Matrix calculation completed successfully",
            "cells": matrix_cells,
        }
    except ValueError as ve:
        logging.warning(f"Validation error in calculate-matrix: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Internal error in calculate-matrix: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-trace")
def calculate_trace(data: CalculatorInput) -> Dict[str, Any]:
    """Przelicza matrycę i zwraca pełen obiekt ze śladem diagnostycznym."""
    try:
        from domain.calculations.service import CalculationService

        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )
        response_data = cast(Any, response.data[0])
        settings = ControlCenterSettings(**response_data)

        calc_service = CalculationService(data=data, settings=settings)
        matrix_cells, trace_data = calc_service.generate_single_trace()

        return {
            "status": "success",
            "message": "Trace generated successfully",
            "cells": matrix_cells,
            "calculation_trace": trace_data,
        }
    except ValueError as ve:
        logging.warning(f"Validation error in calculate-trace: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Internal error in calculate-trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match-body-type", tags=["Calculator"])
def match_body_type_endpoint(
    body_style_raw: str = "",
) -> Dict[str, Any]:
    """Fuzzy-match raw body_style → body_types with score."""
    from core.body_type_matcher import match_body_type

    result = match_body_type(body_style_raw)
    return {
        "matched_body_type_id": result.matched_body_type_id,
        "matched_name": result.matched_name,
        "vehicle_class": result.vehicle_class,
        "score": result.score,
        "match_method": result.match_method,
        "raw_input": result.raw_input,
    }


# ── Readiness Check ─────────────────────────────────────────────────

_engine_name_cache: Optional[Dict[str, int]] = None


def _load_engine_name_map() -> Dict[str, int]:
    global _engine_name_cache
    if _engine_name_cache:
        return _engine_name_cache
    try:
        resp = supabase.table("engines").select("id, name").execute()
        data = cast(Any, resp.data) or []
        # Normalizujemy klucze do wielkich liter bez zbędnych spacji
        _engine_name_cache = {
            str(row["name"]).strip().upper(): int(row["id"]) for row in data
        }
    except Exception as exc:
        logging.warning(f"Nie udało się załadować tabeli engines: {exc}")
        return {}
    return _engine_name_cache


def _resolve_engine_id(engine_name: str) -> Optional[int]:
    if not engine_name or not engine_name.strip():
        return None

    mapping = _load_engine_name_map()
    normalized = engine_name.strip().upper()

    # 1. Dokładne dopasowanie (case-insensitive)
    if normalized in mapping:
        return mapping[normalized]

    # 2. Częściowe dopasowanie (zawiera się w kluczu lub na odwrót)
    for key, fid in mapping.items():
        if key in normalized or normalized in key:
            return fid

    # 3. Fallback: dopasowanie po tagu w nawiasach, np. (PB), (ON), (PHEV)
    import re

    match = re.search(r"\(([A-Z0-9\-]+)\)", normalized)
    if match:
        tag = f"({match.group(1)})"
        for key, fid in mapping.items():
            if tag in key:
                return fid

    # 4. Jeśli nadal nic, a mamy pusty cache (np. błąd DB), spróbujmy przeładować raz jeszcze
    if not mapping:
        global _engine_name_cache
        _engine_name_cache = None
        mapping = _load_engine_name_map()
        if normalized in mapping:
            return mapping[normalized]

    return None


@router.get("/readiness-check", tags=["Calculator"])
def readiness_check(
    samar_class_name: str,
    engine_name: str,
    brand_name: str = "",
    body_type_name: str = "",
    paint_type_name: str = "",
    vehicle_id: str = "",
    zabudowa_type_id: Optional[int] = None,
) -> Dict[str, Any]:
    from core.samar_rv_readiness import check_rv_readiness
    from core.samar_rv import get_samar_class_id

    samar_class_id = get_samar_class_id(samar_class_name)

    if samar_class_id is None and samar_class_name.strip():
        try:
            resp = supabase.table("samar_classes").select("id, name").execute()
            input_norm = samar_class_name.strip().upper().replace("KLASA ", "")
            for row in resp.data or []:
                db_norm = str(row.get("name", "")).strip().upper().replace("KLASA ", "")
                if db_norm == input_norm:
                    samar_class_id = int(row["id"])
                    break
        except Exception as exc:
            logging.warning("Normalizacja SAMAR fallback error: %s", exc)

    fuel_type_id = _resolve_engine_id(engine_name)

    if samar_class_id is None:
        return {
            "overall_status": "not_ready",
            "samar_class_id": None,
            "fuel_type_id": fuel_type_id,
            "resolve_error": f"Nie znaleziono klasy SAMAR: '{samar_class_name}'",
            "checks": [],
            "critical_count": 1,
            "warning_count": 0,
        }

    if fuel_type_id is None:
        return {
            "overall_status": "not_ready",
            "samar_class_id": samar_class_id,
            "fuel_type_id": None,
            "resolve_error": f"Nie rozpoznano silnika: '{engine_name}'",
            "checks": [],
            "critical_count": 1,
            "warning_count": 0,
        }

    from core.body_type_matcher import match_body_type

    resolved_body_type_id: Optional[int] = None
    body_match_info: Dict[str, Any] = {}
    if body_type_name.strip():
        bt_match = match_body_type(body_type_name)
        resolved_body_type_id = bt_match.matched_body_type_id
        body_match_info = {
            "matched_name": bt_match.matched_name,
            "vehicle_class": bt_match.vehicle_class,
            "score": bt_match.score,
            "match_method": bt_match.match_method,
            "raw_input": bt_match.raw_input,
        }

    resolved_paint_type_id: Optional[int] = None
    if paint_type_name.strip():
        try:
            pt_norm = paint_type_name.strip().upper()
            pt_res = supabase.table("paint_types").select("id, name").execute()
            for row in pt_res.data or []:
                if row["name"].strip().upper() == pt_norm:
                    resolved_paint_type_id = int(row["id"])
                    break
            if resolved_paint_type_id is None:
                for row in pt_res.data or []:
                    row_name = row["name"].strip().upper()
                    if row_name in pt_norm or pt_norm in row_name:
                        resolved_paint_type_id = int(row["id"])
                        break
        except Exception as exc:
            logging.warning("Resolve paint_type_name błąd: %s", exc)

    checks = check_rv_readiness(
        samar_class_id=samar_class_id,
        engine_id=fuel_type_id,
        brand_name=brand_name or "UNKNOWN",
        body_type_id=resolved_body_type_id,
        paint_type_id=resolved_paint_type_id,
        rocznik="2026",
        zabudowa_type_id=zabudowa_type_id,
    )

    try:
        svc_res = (
            supabase.table("samar_class_service_rates")
            .select("przebieg_do")
            .eq("klasa_samar_fk", samar_class_id)
            .execute()
        )
        svc_thresholds = [r["przebieg_do"] for r in (svc_res.data or [])]
        if svc_thresholds:
            svc_item = type(checks[0])(
                param="Stawki serwisowe",
                status="ok",
                value=f"TAK, {len(svc_thresholds)} progów",
            )
        else:
            svc_item = type(checks[0])(
                param="Stawki serwisowe",
                status="error",
                value="brak wpisów",
            )
        checks.append(svc_item)
    except Exception:
        pass

    def _simplify_value(c):  # noqa: ANN001, ANN202
        if c.status == "ok":
            return "TAK"
        if c.status == "error":
            return "NIE"
        return c.value

    items = [
        {"param": c.param, "status": c.status, "value": _simplify_value(c)}
        for c in checks
    ]
    error_count = sum(1 for c in checks if c.status == "error")
    warn_count = sum(1 for c in checks if c.status == "warn")

    # ── Walidacja danych pojazdu (synthesis_data) ──────────────────────────
    # Jeśli przekazano vehicle_id, sprawdzamy czy pojazd ma wypełnione
    # kluczowe składowe: marka, model, cena bazowa.
    synthesis_errors: list[Dict[str, str]] = []
    if vehicle_id.strip():
        try:
            v_res = (
                supabase.table("vehicle_synthesis")
                .select("brand, model, synthesis_data")
                .eq("id", vehicle_id.strip())
                .execute()
            )
            if v_res.data:
                vrow = v_res.data[0]
                sd: Dict[str, Any] = vrow.get("synthesis_data") or {}
                cs: Dict[str, Any] = sd.get("card_summary") or {}
                setup: Dict[str, Any] = sd.get("calculator_setup") or {}
                parsed_prices: Dict[str, Any] = cs.get("parsed_prices") or {}

                # Sprawdz czy marka/model wypelnione
                if not vrow.get("brand"):
                    synthesis_errors.append(
                        {"param": "Marka pojazdu", "status": "error", "value": "NIE"}
                    )
                    error_count += 1
                else:
                    items.append(
                        {
                            "param": "Marka pojazdu",
                            "status": "ok",
                            "value": vrow["brand"],
                        }
                    )

                if not vrow.get("model"):
                    synthesis_errors.append(
                        {"param": "Model pojazdu", "status": "error", "value": "NIE"}
                    )
                    error_count += 1
                else:
                    items.append(
                        {
                            "param": "Model pojazdu",
                            "status": "ok",
                            "value": vrow["model"],
                        }
                    )

                # Sprawdz cene bazowa (sciezka identyczna jak w build_calculator_input)
                base_price = (
                    setup.get("catalog_base_price_net")
                    or cs.get("base_price")
                    or parsed_prices.get("base")
                    or (sd.get("universal_features") or {}).get("cena_pojazdu")
                    or (sd.get("computed") or {}).get("estimated_price")
                )
                if not base_price:
                    synthesis_errors.append(
                        {
                            "param": "Cena bazowa (katalogowa)",
                            "status": "error",
                            "value": "BRAK",
                        }
                    )
                    error_count += 1
                else:
                    items.append(
                        {
                            "param": "Cena bazowa (katalogowa)",
                            "status": "ok",
                            "value": str(base_price),
                        }
                    )
            else:
                synthesis_errors.append(
                    {
                        "param": "Pojazd w bazie",
                        "status": "error",
                        "value": "Nie znaleziono ID",
                    }
                )
                error_count += 1
        except Exception as exc:
            logging.warning("Blad walidacji synthesis_data dla %s: %s", vehicle_id, exc)

    items.extend(synthesis_errors)

    if error_count > 0:
        overall = "not_ready"
    else:
        overall = "ready"

    return {
        "overall_status": overall,
        "samar_class_id": samar_class_id,
        "fuel_type_id": fuel_type_id,
        "checks": items,
        "critical_count": error_count,
        "warning_count": warn_count,
        "body_match": body_match_info,
    }
