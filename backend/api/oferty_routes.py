import logging
import time
import uuid
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import supabase
from core.offer_generator import ExcelOfferGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


class OfferItem(BaseModel):
    """Slim payload from frontend cart — backend enriches the rest from DB."""

    id: Optional[str] = None
    brand: str = ""
    model: str = ""
    powertrain: str = ""
    vin_or_config: str = ""
    term: int = 0
    mileage: int = 0
    net_installment: float = 0.0
    contribution: float = 0.0
    margin_pct: Optional[float] = None
    system_recommendation: str = ""
    calculation_data: Dict[str, Any] = {}
    standard_equipment: List[str] = []
    factory_options: List[Any] = []
    dealer_options: List[Any] = []
    matrix_data: Optional[List[Dict[str, Any]]] = None
    notes: str = ""
    overuse_fee: Optional[float] = None  # zł/km — user-picked from dropdown, fallback 0.50


class OfferGenerateRequest(BaseModel):
    client_name: str
    client_nip: str
    client_address: str = ""
    representative: str = ""
    items: List[OfferItem]


def _f(v: Any) -> Optional[float]:
    """Coerce to float — accept str like '12 500,50 zł' too."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(" ", "").replace(" ", "").replace("zł", "")
    s = s.replace(",", ".")
    s = "".join(c for c in s if c.isdigit() or c in ".-")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _normalize_options(raw: Any) -> List[tuple[str, float]]:
    """Return [(name, price_net), ...] from heterogeneous shapes (list of dicts/strings)."""
    out: List[tuple[str, float]] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                name = (entry.get("name") or entry.get("description") or "").strip()
                price = _f(entry.get("price_net"))
                if price is None:
                    price = _f(entry.get("price")) or 0.0
                if name:
                    out.append((name, price or 0.0))
            elif isinstance(entry, str) and entry.strip():
                out.append((entry.strip(), 0.0))
    elif isinstance(raw, dict):
        # service_equipment is a single object with optional components
        name = (raw.get("name") or "").strip()
        price = _f(raw.get("price_net")) or _f(raw.get("price")) or 0.0
        if name:
            out.append((name, price))
        for comp in raw.get("components") or []:
            if isinstance(comp, dict):
                cname = (comp.get("name") or "").strip()
                cprice = _f(comp.get("price_net")) or _f(comp.get("price")) or 0.0
                if cname:
                    out.append((cname, cprice))
    return out


def _build_marketing_name(stan: Dict[str, Any], cs: Dict[str, Any]) -> str:
    parts: List[str] = []
    brand = stan.get("brand") or ""
    model = stan.get("model") or ""
    trim = cs.get("trim_level") or stan.get("trim_level") or ""
    powertrain = cs.get("powertrain") or ""
    transmission = cs.get("transmission") or stan.get("gearbox_name") or ""
    body = cs.get("body_style") or stan.get("body_type_name") or ""
    if brand:
        parts.append(brand.upper())
    if model:
        parts.append(model.upper())
    if trim and trim.lower() not in ("brak", "—"):
        parts.append(trim)
    if powertrain:
        parts.append(powertrain)
    if transmission and transmission.lower() not in ("brak", "—"):
        parts.append(transmission)
    if body and body.lower() not in ("brak", "—"):
        parts.append(body)
    return " ".join(p for p in parts if p).strip()


def _build_in_rate(stan: Dict[str, Any]) -> Dict[str, Any]:
    toggles = stan.get("toggles") or {}
    tire_params = stan.get("tire_params") or {}
    tire_count_mode = tire_params.get("tire_count_mode")
    z_oponami = stan.get("z_oponami")
    if z_oponami is None:
        z_oponami = tire_count_mode and tire_count_mode != "BRAK"

    cost_type = stan.get("service_cost_type") or "ASO"
    include_servicing = bool(toggles.get("include_servicing", stan.get("include_servicing", False)))

    return {
        "ubezp_oc_ac": bool(
            toggles.get("express_pays_insurance", stan.get("express_pays_insurance", False))
        ),
        "serwis": include_servicing,
        "serwis_typ": cost_type if include_servicing else None,
        "opony": bool(z_oponami),
        "opony_klasa": stan.get("klasa_opony_string") or "",
        "opony_rozmiar": tire_params.get("tire_size") or "",
        "opony_zestawy": stan.get("liczba_kompletow_opon") or tire_params.get("tire_set_count"),
        "auto_zastepcze": bool(
            toggles.get("replacement_car", stan.get("replacement_car_enabled", False))
        ),
        "gps": bool(stan.get("add_gsm_subscription", False)),
    }


def _compute_fin_tech_split(
    stan: Dict[str, Any],
    term: int,
    annual_mileage: int,
    applied_margin_pct: Optional[float],
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Re-run LTRKalkulator from stan_json and return (czynsz_finansowy, czynsz_techniczny, laczna_stawka)
    for the (term, annual_mileage) cell. Returns (None, None, None) on any failure."""
    if not stan or not term or not annual_mileage:
        return None, None, None
    try:
        from api.schemas.calculator import CalculatorInput
        from core.LTRKalkulator import LTRKalkulator
        from core.models import ControlCenterSettings

        settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not settings_res.data:
            return None, None, None
        settings = ControlCenterSettings(**cast(Dict[str, Any], settings_res.data[0]))

        calc_input = CalculatorInput(**stan)
        if applied_margin_pct is not None:
            calc_input.pricing_margin_pct = float(applied_margin_pct)

        engine = LTRKalkulator(input_data=calc_input, settings=settings, trace_id="offer-gen")
        # build_matrix() returns full cells with CzynszFinansowy/Techniczny;
        # build_reverse_search_matrix() returns slim cells with only LacznaStawka.
        cells = engine.build_matrix()
        for cell in cells:
            if int(cell.get("Okres", 0)) == int(term) and int(cell.get("Przebieg", 0)) == int(annual_mileage):
                fin_raw = cell.get("CzynszFinansowy")
                tech_raw = cell.get("CzynszTechniczny")
                stawka_raw = cell.get("LacznaStawka")
                fin = float(fin_raw) if fin_raw is not None else None
                tech = float(tech_raw) if tech_raw is not None else None
                stawka = float(stawka_raw) if stawka_raw is not None else None
                return fin, tech, stawka
    except Exception as e:
        logger.info("fin/tech split skipped: %s", str(e)[:200])
    return None, None, None


def _enrich_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Pull stan_json + numer_kalkulacji + matrix breakdown for a single offer item."""
    calc_data = item.get("calculation_data") or {}
    kalk_id = (
        calc_data.get("kalkulacja_id")
        or item.get("kalkulacja_id")
        or calc_data.get("kalkulacja_id")
    )
    vehicle_id = item.get("vehicle_id") or calc_data.get("vehicle_id")

    stan: Dict[str, Any] = {}
    numer = None
    if kalk_id:
        try:
            res = (
                supabase.table("ltr_kalkulacje")
                .select("numer_kalkulacji, stan_json")
                .eq("id", kalk_id)
                .limit(1)
                .execute()
            )
            if res.data:
                row = res.data[0]
                numer = row.get("numer_kalkulacji")
                stan = row.get("stan_json") or {}
        except Exception:
            pass

    cs: Dict[str, Any] = stan.get("card_summary") or {}
    mai: Dict[str, Any] = stan.get("mapped_ai_data") or {}

    factory = _normalize_options(stan.get("factory_options"))
    if not factory:
        factory = _normalize_options(cs.get("paid_options"))
    service = _normalize_options(stan.get("service_options"))
    if not service:
        service = _normalize_options(cs.get("service_equipment"))

    standard = (
        stan.get("standard_equipment")
        or cs.get("standard_equipment")
        or item.get("standard_equipment")
        or []
    )
    if isinstance(standard, list):
        standard_strs = [str(s) for s in standard if s]
    else:
        standard_strs = []

    base_price_net = _f(stan.get("base_price_net")) or _f(calc_data.get("base_price_net")) or 0.0
    factory_total = sum(p for _, p in factory)
    service_total = sum(p for _, p in service)

    contribution_pln = _f(item.get("contribution"))
    if contribution_pln is None or contribution_pln == 0.0:
        contribution_pct = _f(stan.get("initial_deposit_pct")) or 0.0
        contribution_pln = round(base_price_net * contribution_pct / 100, 0) if contribution_pct else 0.0
    elif base_price_net:
        # If frontend sent contribution as raw PLN, derive pct for display
        contribution_pct = round(contribution_pln / base_price_net * 100, 1)
    else:
        contribution_pct = None

    in_rate = _build_in_rate(stan)

    marketing_name = _build_marketing_name(stan, cs) or item.get("powertrain") or "—"

    config_code = (stan.get("configuration_code") or item.get("vin_or_config") or "").strip()
    brand_str = (stan.get("brand") or item.get("brand") or "").strip()
    model_str = (stan.get("model") or item.get("model") or "").strip()
    base_price_for_label = _f(stan.get("base_price_net")) or _f(calc_data.get("base_price_net"))
    if config_code and config_code.lower() not in ("brak", "—", "none"):
        sheet_label = config_code
    elif brand_str or model_str:
        price_token = (
            f" {int(round(base_price_for_label / 1000))}k"
            if base_price_for_label and base_price_for_label > 0
            else ""
        )
        sheet_label = f"{brand_str} {model_str}{price_token}".strip()
    else:
        sheet_label = numer or "Pojazd"

    fin, tech, stawka_recalc = _compute_fin_tech_split(
        stan,
        term=int(item.get("term") or 0),
        annual_mileage=int(item.get("mileage") or 0),
        applied_margin_pct=item.get("margin_pct"),
    )

    enriched = {
        **item,
        "kalk_numer": numer,
        "sheet_label": sheet_label,
        "vin": stan.get("vin") or mai.get("vin") or cs.get("vin"),
        "config_code": stan.get("configuration_code") or item.get("vin_or_config") or "",
        "offer_number": stan.get("offer_number"),
        "marketing_name": marketing_name,
        "trim": cs.get("trim_level") or stan.get("trim_level") or "",
        "transmission": cs.get("transmission") or stan.get("gearbox_name") or "",
        "drive": cs.get("drive_type") or stan.get("drive_type") or "",
        "fuel": cs.get("fuel") or stan.get("fuel") or item.get("powertrain") or "",
        "engine_power_hp": _f(cs.get("power_hp")) or _f(stan.get("power_hp")),
        "body_style": cs.get("body_style") or stan.get("body_type_name") or "",
        "paint_metallic": bool(stan.get("is_metalic", cs.get("is_metalic_paint", False))),
        "samar_category": stan.get("samar_category") or mai.get("samar_category") or "",
        "base_price_net": base_price_net,
        "factory_options_total": factory_total,
        "service_options_total": service_total,
        "factory_options_priced": factory,
        "dealer_options_priced": service,
        "standard": standard_strs,
        "contribution": contribution_pln,
        "contribution_pct": contribution_pct,
        "cost_type": stan.get("service_cost_type") or "ASO",
        "in_rate": in_rate,
        # Re-run calculator to get the fin/tech split — vehicle_matrix_cache
        # only stores LacznaStawka, so we recompute from stan_json with the
        # user's applied margin.
        "financial": fin,
        "technical": tech,
        "overuse_fee": _f(item.get("overuse_fee")) or _f(calc_data.get("opłata_nadprzebieg")) or 0.50,
        "notes": (item.get("notes") or "").strip(),
    }
    return enriched


@router.post("/generate")
def generate_offer(request: OfferGenerateRequest):
    if not request.items:
        raise HTTPException(status_code=400, detail="Koszyk ofertowy jest pusty.")

    try:
        items_dict = [item.model_dump() for item in request.items]
        enriched = [_enrich_item(it) for it in items_dict]

        generator = ExcelOfferGenerator()
        excel_bytes = generator.generate_offer(
            client_name=request.client_name,
            client_nip=request.client_nip,
            client_address=request.client_address,
            representative=request.representative,
            items=enriched,
        )

        client_clean = "".join(c if c.isalnum() else "_" for c in request.client_name)
        filename = (
            f"oferta_{int(time.time())}_{client_clean}_{str(uuid.uuid4())[:8]}.xlsx"
        )

        try:
            supabase.storage.from_("offers_excel").upload(
                path=filename,
                file=excel_bytes,
                file_options={
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )
            file_url = supabase.storage.from_("offers_excel").get_public_url(filename)
        except Exception as storage_err:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Błąd zapisu w chmurze (bucket 'offers_excel'). "
                    f"Sprawdź czy bucket istnieje w Supabase. Błąd: {storage_err}"
                ),
            )

        supabase.table("ltr_offers").insert(
            [
                {
                    "client_name": request.client_name,
                    "client_nip": request.client_nip,
                    "total_calculations": len(items_dict),
                    "offer_snapshot": items_dict,
                    "excel_file_path": file_url,
                }
            ]
        ).execute()

        return {
            "success": True,
            "url": file_url,
            "message": "Oferta została poprawnie wygenerowana i zarchiwizowana.",
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
