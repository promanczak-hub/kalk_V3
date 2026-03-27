"""Endpoint GET /api/param-preview — live preview of backend parameters.

Returns actual values from DB tables that feed into each calculator,
so the frontend LinkedIndicator can show real data in tooltips.
"""

import logging
from typing import Any, Optional, cast

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.database import supabase
from core.LTRSubCalculatorSerwisNew import get_base_service_rate, get_service_multiplier

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Param Preview"])


# ── Response models ──────────────────────────────────────────────


class ServicePreview(BaseModel):
    found: bool = False
    rate_per_km: float = 0.0
    base_rate: float = 0.0
    m_brand: float = 1.0
    m_fuel: float = 1.0
    m_drive: float = 1.0
    m_gearbox: float = 1.0
    total_multiplier: float = 1.0
    type: str = ""
    power_band: str = ""


class TiresPreview(BaseModel):
    found: bool = False
    set_price_net: float = 0.0
    rim_diameter: int = 0
    tire_class: str = ""


class VintagePreview(BaseModel):
    found: bool = False
    correction_pct: float = 0.0
    label: str = ""


class ColorPreview(BaseModel):
    found: bool = False
    correction_pct: float = 0.0
    label: str = ""


class ReplacementCarPreview(BaseModel):
    found: bool = False
    daily_rate_net: float = 0.0
    avg_days_year: float = 0.0


class ParamPreviewResponse(BaseModel):
    service: ServicePreview = ServicePreview()
    tires: TiresPreview = TiresPreview()
    vintage: VintagePreview = VintagePreview()
    color: ColorPreview = ColorPreview()
    replacement_car: ReplacementCarPreview = ReplacementCarPreview()


# ── Helpers ──────────────────────────────────────────────────────


def _fetch_service_preview(
    samar_class_id: int,
    brand_normalized: Optional[str] = None,
    fuel_type: Optional[str] = None,
    drive_type: Optional[str] = None,
    gearbox_type: Optional[str] = None,
    service_type: str = "ASO",
    target_mileage: int = 60000,
) -> ServicePreview:
    """Fetch service rate and multipliers (V3)."""
    try:
        record = get_base_service_rate(samar_class_id, target_mileage)
        if not record:
            return ServicePreview()

        base_rate = float(
            record.get(
                "stawka_aso_per_km"
                if service_type.upper() == "ASO"
                else "stawka_non_aso_per_km",
                0.0,
            )
        )

        m_brand = get_service_multiplier(
            "samar_service_brand_multipliers",
            "brand_normalized",
            (brand_normalized or "").strip().upper(),
        )
        m_fuel = get_service_multiplier(
            "samar_service_fuel_multipliers",
            "fuel_normalized",
            (fuel_type or "").strip().upper(),
        )
        m_drive = get_service_multiplier(
            "samar_service_drive_multipliers",
            "drive_normalized",
            (drive_type or "").strip().upper(),
        )
        m_gearbox = get_service_multiplier(
            "samar_service_gearbox_multipliers",
            "gearbox_normalized",
            (gearbox_type or "").strip().upper(),
        )

        total_multiplier = m_brand * m_fuel * m_drive * m_gearbox
        return ServicePreview(
            found=True,
            rate_per_km=base_rate * total_multiplier,
            base_rate=base_rate,
            m_brand=m_brand,
            m_fuel=m_fuel,
            m_drive=m_drive,
            m_gearbox=m_gearbox,
            total_multiplier=total_multiplier,
            type=service_type.upper(),
        )
    except Exception as exc:
        logger.warning("param-preview service v3 error: %s", exc)
    return ServicePreview()


def _fetch_tires_preview(
    rim_diameter: int,
    tire_class: str,
) -> TiresPreview:
    """Fetch tire set price from koszty_opon."""
    column = tire_class.strip().lower().replace(" ", "_") or "medium"
    try:
        res = (
            supabase.table("koszty_opon")
            .select(column)
            .eq("srednica", rim_diameter)
            .limit(1)
            .execute()
        )
        if res.data:
            row = cast(dict[str, Any], res.data[0])
            val = row.get(column)
            if val is not None:
                return TiresPreview(
                    found=True,
                    set_price_net=float(val),
                    rim_diameter=rim_diameter,
                    tire_class=tire_class,
                )
    except Exception as exc:
        logger.warning("param-preview tires error: %s", exc)
    return TiresPreview(rim_diameter=rim_diameter, tire_class=tire_class)


def _fetch_vintage_preview(vehicle_vintage: str) -> VintagePreview:
    """Fetch vintage correction from ltr_admin_korekta_wr_roczniks."""
    vintage_map = {"current": "bieżący", "previous": "bieżący-1"}
    db_key = vintage_map.get(vehicle_vintage, vehicle_vintage)
    try:
        res = (
            supabase.table("ltr_admin_korekta_wr_roczniks")
            .select("korekta_procent")
            .ilike("rocznik", f"%{db_key}%")
            .limit(1)
            .execute()
        )
        if res.data:
            pct = float(res.data[0].get("korekta_procent", 0.0))
            return VintagePreview(
                found=True,
                correction_pct=pct,
                label=db_key,
            )
    except Exception as exc:
        logger.warning("param-preview vintage error: %s", exc)
    return VintagePreview(label=db_key)


def _fetch_color_preview(is_metalic: bool) -> ColorPreview:
    """Fetch color correction from paint_types."""
    label = "Metalizowany" if is_metalic else "Niemetalizowany"
    try:
        paint_name = "Metalizowany" if is_metalic else "Niemetalizowany"
        res = (
            supabase.table("paint_types")
            .select("wr_correction")
            .ilike("name", f"%{paint_name}%")
            .limit(1)
            .execute()
        )
        if res.data:
            pct = float(res.data[0].get("wr_correction") or 0.0)
            return ColorPreview(found=True, correction_pct=pct, label=label)
    except Exception as exc:
        logger.warning("param-preview color error: %s", exc)
    # Fallback matches samar_rv.py logic
    fallback_pct = 0.0 if is_metalic else -0.01
    return ColorPreview(found=True, correction_pct=fallback_pct, label=label)


def _fetch_replacement_car_preview(
    samar_class_id: int,
) -> ReplacementCarPreview:
    """Fetch replacement car rate from replacement_car_rates."""
    try:
        res = (
            supabase.table("replacement_car_rates")
            .select("daily_rate_net, average_days_per_year")
            .eq("samar_class_id", samar_class_id)
            .limit(1)
            .execute()
        )
        if res.data:
            row = cast(dict[str, Any], res.data[0])
            return ReplacementCarPreview(
                found=True,
                daily_rate_net=float(row.get("daily_rate_net", 0.0)),
                avg_days_year=float(row.get("average_days_per_year", 6.5)),
            )
    except Exception as exc:
        logger.warning("param-preview replacement_car error: %s", exc)
    return ReplacementCarPreview()


@router.get("/param-preview")
def get_param_preview(
    samar_class_id: int = Query(...),
    brand_normalized: Optional[str] = Query(default=None),
    fuel_type: Optional[str] = Query(default=None),
    drive_type: Optional[str] = Query(default=None),
    gearbox_type: Optional[str] = Query(default=None),
    service_type: str = Query(default="ASO"),
    target_mileage: int = Query(default=60000),
    rim_diameter: Optional[int] = Query(default=None),
    tire_class: str = Query(default="Medium"),
    vehicle_vintage: str = Query(default="current"),
    is_metalic: bool = Query(default=False),
) -> ParamPreviewResponse:
    """Returns live parameter preview for LinkedIndicator tooltips."""
    service = _fetch_service_preview(
        samar_class_id,
        brand_normalized,
        fuel_type,
        drive_type,
        gearbox_type,
        service_type,
        target_mileage,
    )

    tires = (
        _fetch_tires_preview(rim_diameter, tire_class)
        if rim_diameter
        else TiresPreview(tire_class=tire_class)
    )
    vintage = _fetch_vintage_preview(vehicle_vintage)
    color = _fetch_color_preview(is_metalic)
    replacement_car = _fetch_replacement_car_preview(samar_class_id)

    return ParamPreviewResponse(
        service=service,
        tires=tires,
        vintage=vintage,
        color=color,
        replacement_car=replacement_car,
    )
