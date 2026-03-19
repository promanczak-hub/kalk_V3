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
        base_price_raw = (
            cs.get("base_price") or parsed_prices.get("base") or 0.0
        )
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
    # Priority: calculator_setup > card_summary
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
        opt_price_net = _parse_price_to_net(
            opt.get("price", 0.0), opt_is_brutto
        )

        is_service = (
            "serwis" in category.lower() or "akcesor" in category.lower()
        )

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


def refresh_matrix_cache_for_vehicles(
    vehicle_ids: list[str],
    job_id: Optional[str] = None,
) -> None:
    """Synchronously refresh the matrix cache for a list of vehicle IDs."""
    if not vehicle_ids:
        return

    logger.info(
        "Refreshing matrix cache for %d vehicles (job=%s)",
        len(vehicle_ids),
        job_id,
    )

    settings_res = (
        supabase.table("control_center").select("*").eq("id", 1).execute()
    )
    if not settings_res.data:
        logger.error("Control center settings not found")
        return
    settings_dict = cast(dict[str, Any], settings_res.data[0])
    settings = ControlCenterSettings(**settings_dict)

    # Fetch vehicles
    v_res = (
        supabase.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .in_("id", vehicle_ids)
        .execute()
    )
    vehicles = v_res.data or []

    records_to_upsert: list[dict[str, Any]] = []
    total_vehicles = len(vehicles)

    for v_idx, v in enumerate(vehicles):
        vid = str(v["id"])

        # ── Progress update ──
        if job_id:
            _cache_progress[job_id] = {
                "total": total_vehicles,
                "done": v_idx,
                "current_vehicle": str(vid),
                "status": "running",
            }

        # ──────────────────────────────────────────────
        # KEY OPTIMISATION: build input ONCE per vehicle
        # ──────────────────────────────────────────────
        base_input = build_calculator_input(v, 0.0, settings)
        if not base_input:
            continue

        for margin in CACHE_MARGINS_PCT:
            # Clone with new margin (no re-parsing of prices/options)
            calc_input = base_input.model_copy(
                update={"pricing_margin_pct": margin}
            )

            # Collect cells from all mileage variants
            all_cells: list[dict[str, Any]] = []

            try:
                # 1. Default grid (40k-80k + base point 35k)
                engine = LTRKalkulator(
                    input_data=calc_input, settings=settings
                )
                all_cells.extend(engine.build_matrix())
            except Exception as e:
                logger.error(
                    "Failed default matrix for %s at margin %.1f%%: %s",
                    vid,
                    margin,
                    e,
                )
                continue


            # Deduplicate by (Okres, Przebieg)
            seen_keys: set[tuple[int, int]] = set()
            for cell in all_cells:
                duration_months = int(cell.get("Okres", 0))
                annual_mileage = int(cell.get("Przebieg", 0))
                monthly_price_net = float(cell.get("LacznaStawka", 0.0))

                cell_key = (duration_months, annual_mileage)
                if cell_key in seen_keys:
                    continue
                seen_keys.add(cell_key)

                if (
                    duration_months > 0
                    and annual_mileage > 0
                    and monthly_price_net > 0
                ):
                    records_to_upsert.append(
                        {
                            "vehicle_id": str(vid),
                            "duration_months": duration_months,
                            "annual_mileage": annual_mileage,
                            "margin_pct": margin,
                            "base_price_net": float(calc_input.base_price_net),
                            "monthly_price_net": monthly_price_net,
                        }
                    )

    if records_to_upsert:
        logger.info(
            "Upserting %d matrix cells into cache", len(records_to_upsert)
        )
        chunk_size = 1000
        for i in range(0, len(records_to_upsert), chunk_size):
            chunk = records_to_upsert[i : i + chunk_size]
            try:
                supabase.table("vehicle_matrix_cache").upsert(
                    chunk,
                    on_conflict="vehicle_id,duration_months,annual_mileage,margin_pct",
                ).execute()
            except Exception as e:
                logger.error("Failed to upsert cache chunk: %s", e)

    # ── Final progress ──
    if job_id:
        _cache_progress[job_id] = {
            "total": total_vehicles,
            "done": total_vehicles,
            "current_vehicle": None,
            "status": "done",
        }

    logger.info("Matrix cache refresh complete")



def trigger_all_vehicles_cache_refresh() -> None:
    """Fetches all verified vehicles and refreshes their matrix cache."""
    try:
        v_res = (
            supabase.table("vehicle_synthesis")
            .select("id")
            .eq("verification_status", "completed")
            .execute()
        )
        vehicles_list = cast(list[dict[str, Any]], v_res.data or [])
        ids = [str(v["id"]) for v in vehicles_list]
        if ids:
            refresh_matrix_cache_for_vehicles(ids)
    except Exception as e:
        logger.error("Failed to trigger bulk matrix cache refresh: %s", e)


def calculate_live_ltr_tile(
    vehicle_id: str,
    duration_months: int,
    annual_mileage: int,
) -> Optional[float]:
    """
    On-demand calculation of a single LTR tile for a chosen duration/mileage.
    Returns the monthly_price_net if successful, otherwise None.
    """
    try:
        # 1. Load settings and vehicle data
        settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not settings_res.data:
            logger.error("calculate_live_ltr_tile: Settings not found")
            return None
        settings_dict = cast(dict[str, Any], settings_res.data[0])
        settings = ControlCenterSettings(**settings_dict)

        v_res = (
            supabase.table("vehicle_synthesis")
            .select("id, synthesis_data")
            .eq("id", vehicle_id)
            .execute()
        )
        if not v_res.data:
            return None
        
        vehicle_row = cast(dict[str, Any], v_res.data[0])
        
        # 2. Build input parameters (margin = 0.0, to be applied later or here)
        # Note: In cache we store margin=0.0. We should return the 0.0 margin price 
        # so that rpc_reverse_search or get_price_for_params can apply the active margin from the frontend payload.
        # Actually, get_price_for_params just returns whatever is there, wait!
        # The frontend expects the RAW price from cache (margin 0.0), and the exact tile margin will be added by RPC... wait, `get_price_for_params` currently is called from frontend without margin input, and it just returns the cache value (which is margin=0.0). Oh wait, no!
        # Let's see what get_price_for_params returns.
        base_input = build_calculator_input(vehicle_row, 0.0, settings)
        if not base_input:
            return None
            
        calc_input = base_input.model_copy()
        calc_input.pricing_margin_pct = 0.0
        
        # Inject the exact pair we want
        req_total_km = int(round((annual_mileage / 12) * duration_months))
        calc_input.okres_bazowy = duration_months
        calc_input.przebieg_bazowy = req_total_km
        
        # 3. Calculate grid
        engine = LTRKalkulator(input_data=calc_input, settings=settings)
        matrix_cells = engine.build_matrix()
        
        # 4. Find the exact cell
        for cell in matrix_cells:
            months = int(cell.get("Okres", 0))
            km_py = int(cell.get("Przebieg", 0))
            if months == duration_months and km_py == annual_mileage:
                price = float(cell.get("LacznaStawka", 0.0))
                if price > 0:
                    return price
                    
        return None
    except Exception as e:
        logger.error("Failed live LTR calculation for %s: %s", vehicle_id, e)
        return None

