"""Single source of truth: turn (vehicle_id [, kalkulacja_id, overrides])
into a fully‑resolved `CalculatorInput`.

Multiple callers used to construct payloads independently — backend
matrix‑cache job from `vehicle_synthesis.calculator_setup`, two frontend
builders (one from `synthesis_data`, one from `ltr_kalkulacje.stan_json`),
plus ad‑hoc scripts. They drifted on defaults (paint_type_id, financing
margin, etc.). This endpoint replaces all of them with one canonical
resolution: backend reads `vehicle_synthesis` (source of truth for
vehicle‑level defaults), optionally overlays `stan_json` (kalkulacja‑level
state), then applies request‑time `overrides`. Clients post the returned
payload verbatim to `/api/calculate-matrix`.
"""

import logging
from typing import Any, Dict, Optional, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.schemas.calculator import CalculatorInput
from core.database import supabase
from core.matrix_cache_job import build_calculator_input
from core.models import ControlCenterSettings

router = APIRouter()
logger = logging.getLogger(__name__)


class ResolveInputRequest(BaseModel):
    vehicle_id: str = Field(..., description="UUID pojazdu w `vehicle_synthesis`")
    kalkulacja_id: Optional[str] = Field(
        default=None,
        description=(
            "UUID kalkulacji w `ltr_kalkulacje`. Gdy podane, wybrane pola "
            "z `stan_json` (toggles, financial_params, axes, factory/service "
            "options) nadpisują vehicle‑level defaulty."
        ),
    )
    margin_pct: float = Field(
        default=0.0,
        description=(
            "Marża sprzedażowa (%) wstrzyknięta do `pricing_margin_pct`. "
            "Dla matrix‑cache trzymamy 0; UI nakłada własną marżę po stronie cell."
        ),
    )
    overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Płaski słownik nadpisań pól `CalculatorInput` (np. "
            "{'pricing_margin_pct': 5, 'add_hook_installation': true}). "
            "Nieznane klucze są ignorowane."
        ),
    )


# Pola ze `stan_json`, które uznajemy za "kalkulacja state" — nadpisują
# vehicle‑level defaulty. Lista jest świadomie wąska, by nie wciągnąć
# zupełnie syntetycznych pól (`brand`, `model`, `card_summary` itd.).
_STAN_JSON_OVERLAY_FIELDS = frozenset({
    "discount_pct",
    "pricing_margin_pct",
    "wibor_pct",
    "margin_pct",
    "depreciation_pct",
    "initial_deposit_pct",
    "manual_wr_correction",
    "z_oponami",
    "klasa_opony_string",
    "srednica_felgi",
    "liczba_kompletow_opon",
    "korekta_kosztu_opon",
    "koszt_opon_korekta",
    "include_servicing",
    "service_cost_type",
    "replacement_car_enabled",
    "express_pays_insurance",
    "add_gsm_subscription",
    "add_hook_installation",
    "add_grid_dismantling",
    "add_registration",
    "add_sales_prep",
    "korekta_kosztu_przygotowania",
    "vehicle_vintage",
    "is_metalic",
    "paint_type_id",
    "matrix_km_mode",
    "matrix_contract_km_step",
    "okres_bazowy",
    "przebieg_bazowy",
    "factory_options",
    "service_options",
    "inne_koszty_serwisowania_netto",
    "pakiet_serwisowy",
    "samar_category",
    "engine_name",
    "body_type_name",
    "drive_type",
    "gearbox_name",
    "zabudowa_type_id",
})


def _coerce_overlay_value(field_name: str, raw: Any) -> Any:
    """Drop None for non‑Optional bools/strings to let CalculatorInput
    defaults take over. Lists/dicts pass through, scalars are coerced."""
    if raw is None:
        return None
    return raw


@router.post("/calculator/resolve-input", tags=["Calculator"])
def resolve_calculator_input(req: ResolveInputRequest) -> Dict[str, Any]:
    """Return a fully‑resolved `CalculatorInput` JSON.

    Resolution order (later wins for the listed `_STAN_JSON_OVERLAY_FIELDS`):
      1. `build_calculator_input(vehicle_synthesis row)`  — canonical defaults
      2. `ltr_kalkulacje.stan_json` overlay (if `kalkulacja_id` provided)
      3. `overrides` from the request body
      4. `margin_pct` injected to `pricing_margin_pct`
    """
    cc_resp = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not cc_resp.data:
        raise HTTPException(status_code=500, detail="control_center settings missing")
    settings = ControlCenterSettings(**cast(Dict[str, Any], cc_resp.data[0]))

    v_resp = (
        supabase.table("vehicle_synthesis")
        .select("*")
        .eq("id", req.vehicle_id)
        .execute()
    )
    if not v_resp.data:
        raise HTTPException(status_code=404, detail=f"vehicle {req.vehicle_id} not found")
    vehicle_row = cast(Dict[str, Any], v_resp.data[0])

    base_input: Optional[CalculatorInput] = build_calculator_input(
        vehicle_row, margin_pct=req.margin_pct, settings=settings
    )
    if base_input is None:
        raise HTTPException(
            status_code=422,
            detail=f"build_calculator_input could not derive a valid input for vehicle {req.vehicle_id}",
        )

    # 2. stan_json overlay — only the calc‑level fields, never identity (vehicle_id, brand, ...)
    if req.kalkulacja_id:
        k_resp = (
            supabase.table("ltr_kalkulacje")
            .select("stan_json")
            .eq("id", req.kalkulacja_id)
            .execute()
        )
        if k_resp.data:
            stan = cast(Dict[str, Any], (k_resp.data[0] or {}).get("stan_json") or {})
            for key, raw in stan.items():
                if key not in _STAN_JSON_OVERLAY_FIELDS:
                    continue
                value = _coerce_overlay_value(key, raw)
                if value is None and key not in {"wibor_pct", "margin_pct", "depreciation_pct"}:
                    # Optional[float] fields can legitimately stay None
                    continue
                try:
                    setattr(base_input, key, value)
                except Exception as exc:
                    logger.debug("overlay skip %s=%r: %s", key, raw, exc)

    # 3. request‑time overrides — narrow whitelist via Pydantic; unknown keys silently dropped
    if req.overrides:
        for key, raw in req.overrides.items():
            if not hasattr(base_input, key):
                continue
            try:
                setattr(base_input, key, raw)
            except Exception as exc:
                logger.debug("override skip %s=%r: %s", key, raw, exc)

    # Re‑inject margin_pct (it lives in CalculatorInput as `pricing_margin_pct`)
    base_input.pricing_margin_pct = float(req.margin_pct)

    return {
        "status": "success",
        "calculator_input": base_input.model_dump(mode="json"),
    }
