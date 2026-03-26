"""Matrix cache job — batch LTR calculation for vehicle_matrix_cache.

Optimised to build CalculatorInput ONCE per vehicle and reuse it
across margin/mileage variants via Pydantic model_copy().
"""

import logging

from typing import Any, Dict, Optional, cast

from core.database import supabase
from core.models import ControlCenterSettings
from api.schemas.calculator import CalculatorInput, VehicleOptions
from core.LTRKalkulator import LTRKalkulator
from core.price_parser import parse_price_string

logger = logging.getLogger(__name__)


def _upsert_job(
    vehicle_id: str,
    status: str,
    error_code: str | None = None,
    error_detail: str | None = None,
    celery_task_id: str | None = None,
    monthly_price: float | None = None,
) -> None:
    """Persist Celery task status to calculation_jobs — never raises."""
    try:
        supabase.rpc(
            "upsert_calculation_job",
            {
                "p_vehicle_id": vehicle_id,
                "p_status": status,
                "p_error_code": error_code,
                "p_error_detail": error_detail,
                "p_celery_task_id": celery_task_id,
                "p_monthly_price": monthly_price,
            },
        ).execute()
    except Exception as exc:
        logger.warning("[JOBS] upsert_calculation_job failed silently: %s", exc)

# Standard configurations for pricing matrix
CACHE_MARGINS_PCT = [0.0]  # Only base cost; margin applied dynamically in RPC

# Extra mileage variants removed — build_matrix() now covers 10k-80k km/yr
# natively across all period buckets (12-84 months).

# ── In-memory progress store ──
_cache_progress: dict[str, dict[str, Any]] = {}


def get_cache_progress(job_id: str) -> Optional[Dict[str, Any]]:
    """Return current progress for a given job_id."""
    return _cache_progress.get(job_id)


def _parse_price_to_net(price_val: Any, is_brutto: bool) -> float:
    """Parse a price value and convert to netto if brutto.

    Uses price_parser for strings, direct float conversion otherwise.
    """
    try:
        if isinstance(price_val, str):
            parsed = parse_price_string(price_val)
            if parsed is None:
                return 0.0
            val = parsed.value
            # If parsed string has explicit tax_type, use that instead of caller's flag
            if parsed.tax_type == "brutto":
                return round(val / 1.23, 2)
            if parsed.tax_type == "netto":
                return val
            # No explicit label — fall through to caller's flag
        else:
            val = float(price_val)

        if is_brutto:
            return round(val / 1.23, 2)
        return val
    except Exception:
        return 0.0


def _detect_price_domain(card_summary: Dict[str, Any]) -> str:
    """Detect price domain with robust fallback chain.

    Priority:
    1. Explicit ``_price_domain`` field (set by price_validator)
    2. Explicit label in ``base_price`` / ``total_price`` string
    3. "unknown" — caller MUST handle this case
    """
    explicit_domain = card_summary.get("_price_domain", "unknown")
    if explicit_domain in ("netto", "brutto"):
        return explicit_domain

    # Try to extract from the raw price strings
    for field in ("base_price", "total_price"):
        raw = card_summary.get(field)
        if isinstance(raw, str):
            lower = raw.lower()
            if "netto" in lower:
                return "netto"
            if "brutto" in lower:
                return "brutto"

    return "unknown"


def build_calculator_input(
    vehicle_row: Dict[str, Any],
    margin_pct: float,
    settings: ControlCenterSettings,
    override_discount_pct: Optional[float] = None,
) -> Optional[CalculatorInput]:
    """Build CalculatorInput from a vehicle_synthesis row.

    Aligns with frontend useVehicleFinancing.ts defaults.
    """
    vid = vehicle_row.get("id")
    sd = vehicle_row.get("synthesis_data") or {}
    cs = sd.get("card_summary") or {}
    setup = sd.get("calculator_setup") or {}

    # ── Price domain detection (robust chain) ──
    price_domain = _detect_price_domain(cs)
    is_brutto = price_domain == "brutto"

    if price_domain == "unknown":
        logger.warning(
            "[MATRIX CACHE] vehicle=%s: _price_domain='unknown' — "
            "nie udało się ustalić netto/brutto. Domyślnie traktuję "
            "jako BRUTTO.",
            vid,
        )

    # ── Base price extraction ──
    # Priority: calculator_setup > card_summary > parsed_prices
    base_price_raw = setup.get("catalog_base_price_net")
    if base_price_raw:
        base_price_net = float(base_price_raw)
    else:
        parsed_prices = cs.get("parsed_prices") or {}
        base_price_raw = cs.get("base_price") or parsed_prices.get("base") or 0.0
        if not base_price_raw:
            univ = sd.get("universal_features") or {}
            comp = sd.get("computed") or {}
            base_price_raw = (
                univ.get("cena_pojazdu") or comp.get("estimated_price") or 0.0
            )

        if not base_price_raw:
            logger.warning("Skipping %s: No base_price found", vid)
            return None
        base_price_net = _parse_price_to_net(base_price_raw, is_brutto)

    if base_price_net <= 0:
        logger.warning("Skipping %s: base_price_net invalid", vid)
        return None

    # ── Discount extraction ──
    # Priority: override > calculator_setup > card_summary
    if override_discount_pct is not None:
        discount_pct = float(override_discount_pct)
    else:
        discount_pct = float(
            setup.get("discount", {}).get("active_discount_pct")
            or cs.get("suggested_discount_pct")
            or 0.0
        )

    # ── Metalic paint ──
    # Priority: calculator_setup > card_summary
    is_metalic = setup.get("is_metalic")
    if is_metalic is None:
        is_metalic = cs.get("is_metalic_paint", False)

    # ── Paid options ──
    factory_options_list: list[VehicleOptions] = []
    service_options_list: list[VehicleOptions] = []

    for opt in cs.get("paid_options", []):
        if not isinstance(opt, dict):
            continue
        name = opt.get("name", "Opcja")
        category = (opt.get("category") or "Fabryczna").strip()
        opt_price_type = (opt.get("price_type") or price_domain).lower()
        opt_is_brutto = opt_price_type == "brutto" or (
            opt_price_type == "unknown" and is_brutto
        )
        opt_price_net = _parse_price_to_net(opt.get("price", 0.0), opt_is_brutto)

        is_service = "serwis" in category.lower() or "akcesor" in category.lower()

        option_item = VehicleOptions(
            name=name,
            price_net=opt_price_net,
            price_gross=round(opt_price_net * 1.23, 2),
            no_discount=is_service,
            include_in_wr=not is_service,
        )

        if is_service:
            service_options_list.append(option_item)
        else:
            factory_options_list.append(option_item)

    # ── Toggles ──
    toggles = setup.get("toggles") or {}
    z_oponami = toggles.get("include_tires", True)  # Custom fallback
    include_servicing = toggles.get("include_servicing", True)
    replacement_car = toggles.get("replacement_car", True)
    add_hook = toggles.get("hook_installation", False)

    # ── Tire parameters ──
    tire_params = setup.get("tire_params") or {}
    klasa_opony = tire_params.get("tire_class", "Medium")
    srednica_felgi = tire_params.get("rim_diameter")

    if not srednica_felgi:
        # Fallback to simple regex on wheels field
        import re

        wheels_str = cs.get("wheels", "")
        if wheels_str and wheels_str != "Brak":
            m = re.search(r"\b(1[3-9]|2[0-4])\b", str(wheels_str))
            if m:
                srednica_felgi = int(m.group(1))

    if not srednica_felgi:
        # Final fallback from computed or default 18
        computed = sd.get("computed") or {}
        srednica_felgi = int(computed.get("srednica_felgi") or 18)

    # ── Final input construction ──
    calc_input = CalculatorInput(
        vehicle_id=str(vid),
        base_price_net=base_price_net,
        discount_pct=discount_pct,
        factory_options=factory_options_list,
        service_options=service_options_list,
        pricing_margin_pct=margin_pct,
        margin_pct=float(settings.bank_spread or 2.0),
        wibor_pct=float(settings.default_wibor or 5.85),
        matrix_km_mode="annual",
        okres_bazowy=48,
        przebieg_bazowy=140000,
        z_oponami=z_oponami,
        klasa_opony_string=klasa_opony,
        srednica_felgi=srednica_felgi,
        include_servicing=include_servicing,
        replacement_car_enabled=replacement_car,
        add_hook_installation=add_hook,
        service_cost_type=setup.get("service_cost_type", "ASO"),
        is_metalic=is_metalic,
    )

    return calc_input


def process_single_kalkulacja_matrix_task(
    kalkulacja_id: str,
    celery_task_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Calculate and cache 116 matrix cells for a given kalkulacja."""
    task_trace_id = trace_id or celery_task_id or "UNKNOWN_TRACE"
    logger.info("Starting process_single_kalkulacja_matrix_task for kalkulacja_id=%s [Trace: %s]", kalkulacja_id, task_trace_id)

    # 1. Fetch kalkulacja
    res = supabase.table("ltr_kalkulacje").select("*").eq("id", kalkulacja_id).execute()
    if not res.data:
        logger.error("process_single_kalkulacja_matrix_task: Kalkulacja %s not found [Trace: %s]", kalkulacja_id, task_trace_id)
        return

    kalk_row = res.data[0]
    stan_json = kalk_row.get("stan_json") or {}
    vehicle_id = stan_json.get("vehicle_id")

    if not vehicle_id:
        logger.error("Kalkulacja %s has no vehicle_id. Skipping matrix generation.", kalkulacja_id)
        return

    # Track: running
    _upsert_job(vehicle_id, "running", celery_task_id=celery_task_id)

    # 2. Load CC settings (needed for both direct parse and fallback)
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not settings_res.data:
        logger.error("process_single_kalkulacja_matrix_task: Control center settings not found")
        _upsert_job(vehicle_id, "failed", error_code="NO_CC_SETTINGS", error_detail="control_center table empty")
        return
    settings_dict = cast(dict[str, Any], settings_res.data[0])
    settings = ControlCenterSettings(**settings_dict)

    # 3. Build CalculatorInput — try direct parse first, fallback to build_calculator_input
    calc_input: CalculatorInput | None = None
    try:
        calc_input = CalculatorInput(**stan_json)
    except Exception as direct_err:
        logger.warning(
            "Direct stan_json parse failed for kalkulacja %s (likely raw synthesisData). "
            "Falling back to build_calculator_input. Error: %s [Trace: %s]",
            kalkulacja_id, str(direct_err)[:200], task_trace_id,
        )
        # Fallback: fetch vehicle from vehicle_synthesis and build input properly
        v_res = supabase.table("vehicle_synthesis").select("*").eq("id", vehicle_id).execute()
        if not v_res.data:
            msg = f"Direct parse failed AND vehicle {vehicle_id} not found in vehicle_synthesis"
            logger.error(msg)
            _upsert_job(vehicle_id, "failed", error_code="VEHICLE_NOT_FOUND", error_detail=msg)
            return
        try:
            calc_input = build_calculator_input(v_res.data[0], margin_pct=0.0, settings=settings)
        except Exception as build_err:
            msg = str(build_err)[:500]
            logger.error("build_calculator_input fallback also failed for %s: %s", vehicle_id, build_err)
            _upsert_job(vehicle_id, "failed", error_code="BUILD_INPUT_ERROR", error_detail=msg)
            return

    if not calc_input:
        logger.error("CalculatorInput is None for kalkulacja %s / vehicle %s", kalkulacja_id, vehicle_id)
        _upsert_job(vehicle_id, "failed", error_code="NO_BASE_PRICE", error_detail="build_calculator_input returned None")
        return

    # CRITICAL: Force pricing_margin_pct to 0.0 for cache generation!
    # The cache must store base prices (0% sales margin).
    # The sales margin is added dynamically by the frontend in Reverse Search.
    calc_input.pricing_margin_pct = 0.0

    # 4. Generate Matrix
    try:
        engine = LTRKalkulator(input_data=calc_input, settings=settings, trace_id=task_trace_id)
        all_cells = engine.build_matrix()
    except Exception as e:
        msg = str(e)[:500]
        logger.error("Failed matrix build for kalkulacja %s: %s [Trace: %s]", kalkulacja_id, e, task_trace_id)
        _upsert_job(vehicle_id, "failed", error_code="CALC_ERROR", error_detail=msg)
        return

    # 5. Upsert vehicle matrix cache
    records_to_upsert: list[dict[str, Any]] = []

    tire_class = calc_input.klasa_opony_string
    service_type = calc_input.service_cost_type
    margin = calc_input.pricing_margin_pct
    discount_val = calc_input.discount_pct
    base_price_net = float(calc_input.base_price_net)
    best_price: float | None = None

    seen_keys: set[tuple[int, int]] = set()
    for cell in all_cells:
        duration_months = int(cell.get("Okres", 0))
        annual_mileage = int(cell.get("Przebieg", 0))
        monthly_price_net = float(cell.get("LacznaStawka", 0.0))

        cell_key = (duration_months, annual_mileage)
        if cell_key in seen_keys:
            continue
        seen_keys.add(cell_key)

        if duration_months > 0 and annual_mileage > 0 and monthly_price_net > 0:
            # Track cheapest cell for jobs dashboard
            if best_price is None or monthly_price_net < best_price:
                best_price = monthly_price_net
            records_to_upsert.append(
                {
                    "vehicle_id": str(vehicle_id),
                    "kalkulacja_id": kalkulacja_id,
                    "duration_months": duration_months,
                    "annual_mileage": annual_mileage,
                    "margin_pct": margin,
                    "discount_pct": discount_val,
                    "base_price_net": base_price_net,
                    "monthly_price_net": monthly_price_net,
                    "tire_class": tire_class,
                    "service_type": service_type,
                }
            )

    if records_to_upsert:
        logger.info("Upserting %d matrix cells for kalkulacja %s", len(records_to_upsert), kalkulacja_id)
        chunk_size = 500
        for i in range(0, len(records_to_upsert), chunk_size):
            chunk = records_to_upsert[i : i + chunk_size]
            try:
                supabase.table("vehicle_matrix_cache").upsert(
                    chunk,
                    on_conflict="kalkulacja_id,duration_months,annual_mileage",
                ).execute()
            except Exception as e:
                logger.error("Failed to upsert cache chunk %s: %s", kalkulacja_id, e)
                _upsert_job(vehicle_id, "failed", error_code="DB_UPSERT_ERROR", error_detail=str(e)[:300])
                return

        # Track: done
        _upsert_job(vehicle_id, "done", monthly_price=best_price)
        logger.info("Matrix cache refresh complete for kalkulacja %s", kalkulacja_id)
    else:
        _upsert_job(vehicle_id, "failed", error_code="NO_MATRIX_CELLS", error_detail="build_matrix() returned 0 valid cells")
        logger.warning("No valid matrix cells generated for kalkulacja %s", kalkulacja_id)


def refresh_matrix_cache_for_vehicles(vehicle_ids: list[str]) -> None:
    """Generate default LTR matrix cache for newly extracted/updated vehicles.
    
    Creates a system-generated record in ltr_kalkulacje and runs the matrix calculation.
    """
    logger.info("Auto-refreshing matrix cache for vehicles: %s", vehicle_ids)
    
    # 1. Fetch vehicles
    v_res = supabase.table("vehicle_synthesis").select("*").in_("id", vehicle_ids).execute()
    vehicles = v_res.data or []
    
    # 2. Fetch CC settings
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not settings_res.data:
        logger.error("refresh_matrix_cache_for_vehicles: Control center settings not found")
        return
    settings_dict = cast(dict[str, Any], settings_res.data[0])
    settings = ControlCenterSettings(**settings_dict)
    
    import uuid
    from datetime import datetime
    
    for row in vehicles:
        vid = row["id"]
        # Track: queued before building input
        _upsert_job(str(vid), "queued")
        # Force 0.0 margin for caching to support Reverse Search (Zero-Margin DB)
        try:
            calc_input = build_calculator_input(row, margin_pct=0.0, settings=settings)
        except Exception as e:
            msg = str(e)[:400]
            logger.error("Error building calculator input for %s: %s", vid, e)
            _upsert_job(str(vid), "failed", error_code="BUILD_INPUT_ERROR", error_detail=msg)
            continue

        if not calc_input:
            logger.warning("Failed to build CalculatorInput for vehicle %s. Skipping auto-cache.", vid)
            _upsert_job(str(vid), "failed", error_code="NO_BASE_PRICE", error_detail="build_calculator_input returned None")
            continue
            
        stan_json = calc_input.model_dump()
        stan_json["source"] = "auto_extract"
        
        # UI metadata often required by front/routes
        stan_json["brand"] = row.get("brand", "")
        stan_json["model"] = row.get("model", "")
        stan_json["samar_category"] = row.get("synthesis_data", {}).get("mapped_ai_data", {}).get("samar_category", "")
        stan_json["engine_name"] = row.get("synthesis_data", {}).get("mapped_ai_data", {}).get("engine_class", "")
        
        brand = stan_json["brand"]
        model = stan_json["model"]
        dane_pojazdu = f"{brand} {model}".strip() if brand or model else "System Auto-Extract"
        
        now = datetime.now()
        short_uuid = uuid.uuid4().hex[:6].upper()
        numer_kalkulacji = f"AUTO/{now.year}/{now.month:02d}/{short_uuid}"
        
        kalk_data = {
            "numer_kalkulacji": numer_kalkulacji,
            "status": "szkic_vertex",
            "stan_json": stan_json,
            "dane_pojazdu": dane_pojazdu,
            "cena_netto": float(calc_input.base_price_net),
        }
        
        try:
            # Avoid spamming the calculation table by checking if an auto_extract already exists
            exist_res = supabase.table("ltr_kalkulacje").select("id").eq("stan_json->>vehicle_id", vid).eq("stan_json->>source", "auto_extract").execute()
            if exist_res.data:
                new_kalk_id = exist_res.data[0]["id"]
                kalk_data["updated_at"] = now.isoformat()
                supabase.table("ltr_kalkulacje").update(kalk_data).eq("id", new_kalk_id).execute()
                logger.info("Updated exiting auto-kalkulacja %s for vehicle %s", new_kalk_id, vid)
            else:
                ins_res = supabase.table("ltr_kalkulacje").insert(kalk_data).execute()
                if not ins_res.data:
                    logger.error("Failed to insert auto-kalkulacja for vehicle %s", vid)
                    continue
                new_kalk_id = ins_res.data[0]["id"]
                logger.info("Created new auto-kalkulacja %s for vehicle %s", new_kalk_id, vid)
            
            # Generate matrices synchronously
            process_single_kalkulacja_matrix_task(new_kalk_id)
        except Exception as e:
            logger.error("Error inserting/generating matrix for auto-kalkulacja of %s: %s", vid, e)
