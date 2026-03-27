"""FastAPI routes for the reverse_search scoring engine."""

import hashlib
import json
import logging

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult

from core.database import supabase
from core.celery_app import celery_app
from core.models_scoring_search import (
    AvailableFiltersRequest,
    ScoringSearchRequest,
    ScoringSearchResponse,
    ScoringSearchMatch,
    InitialDataResponse,
    SimilarVehicleMatch,
    TrimsAndOptionsRequest,
    TrimsAndOptionsResponse,
    OptionItem,
    PriceForParamsResponse,
    SimilarBatchRequest,
    SimilarBatchResponse,
)
from typing import List, Dict
from core.redis_cache import (
    _get_client,
    _PREFIX,
    get_cache_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring_search"])

# ── TTL constants ──────────────────────────────────────────────────────────────
_TTL_INITIAL_DATA = 3600  # 1 hour  — changes only when vehicles are added
_TTL_FILTERS = 300  # 5 min   — depends on vehicle DB state
_TTL_SEARCH = 120  # 2 min   — user results; short enough to stay fresh


# ── Helpers ───────────────────────────────────────────────────────────────────


def _redis_get(key: str) -> Any | None:
    """Safe Redis GET — returns None on any error."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.debug("Redis GET error [%s]: %s", key, exc)
        return None


def _redis_set(key: str, value: Any, ttl: int) -> None:
    """Safe Redis SETEX — silently skips on any error."""
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("Redis SET error [%s]: %s", exc)


def _params_hash(payload: str) -> str:
    return hashlib.md5(payload.encode(), usedforsecurity=False).hexdigest()


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/scoring-search/available-filters")
def get_available_filters(request: AvailableFiltersRequest) -> dict[str, Any]:
    """Get dynamic facets (enums, ranges) generated directly from DB evidence."""
    params_hash = _params_hash(request.model_dump_json())
    cache_key = f"{_PREFIX}filters:{params_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: available-filters [%s]", params_hash)
        return cached

    sb = supabase
    try:
        resp = sb.rpc(
            "rpc_get_available_filters",
            {
                "p_brands": request.brands,
                "p_models": request.models,
                "p_body_types": request.body_types,
                "p_samar_class_ids": request.samar_class_ids,
                "p_current_filters": request.current_filters or {},
            },
        ).execute()

        result: dict[str, Any] = resp.data or {}
        _redis_set(cache_key, result, _TTL_FILTERS)
        return result
    except Exception as e:
        logger.exception("Error calling rpc_get_available_filters: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch available filters: {e}"
        )


@router.post("/scoring-search/search")
def run_scoring_search(request: ScoringSearchRequest) -> ScoringSearchResponse:
    """Run search scoring against Must-Have and Nice-To-Have criteria."""
    params_hash = _params_hash(request.model_dump_json())
    cache_key = f"{_PREFIX}search:{params_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: search [%s]", params_hash)
        matches = [ScoringSearchMatch(**row) for row in cached["results_raw"]]
        page_results = matches[request.offset : request.offset + request.limit]
        return ScoringSearchResponse(results=page_results, total_count=cached["total"])

    sb = supabase
    try:
        req_list = [req.model_dump() for req in request.requirements]

        resp = sb.rpc(
            "rpc_reverse_search",
            {
                "p_brands": request.brands,
                "p_models": request.models,
                "p_samar_class_ids": request.samar_class_ids,
                "p_trims": request.trims,
                "p_requirements": req_list,
            },
        ).execute()

        all_matches = [ScoringSearchMatch(**row) for row in resp.data]

        # Cache all raw results (pagination applied after cache read)
        _redis_set(
            cache_key,
            {"results_raw": resp.data, "total": len(all_matches)},
            _TTL_SEARCH,
        )

        page_results = all_matches[request.offset : request.offset + request.limit]
        return ScoringSearchResponse(results=page_results, total_count=len(all_matches))
    except Exception as e:
        logger.exception("Error calling rpc_reverse_search: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/scoring-search/initial-data", response_model=InitialDataResponse)
def get_initial_data() -> InitialDataResponse:
    """Get unique brands, models, and Samar classes for the Multi-Filter UI."""
    cache_key = f"{_PREFIX}initial_data"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: initial-data")
        return InitialDataResponse(**cached)

    sb = supabase
    try:
        resp = sb.rpc("rpc_get_scoring_initial_data").execute()
        result = InitialDataResponse(**resp.data)
        _redis_set(cache_key, result.model_dump(), _TTL_INITIAL_DATA)
        return result
    except Exception as e:
        logger.exception("Error calling rpc_get_scoring_initial_data: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch initial data: {e}"
        )


@router.post(
    "/scoring-search/trims-and-options", response_model=TrimsAndOptionsResponse
)
def get_trims_and_options(request: TrimsAndOptionsRequest) -> TrimsAndOptionsResponse:
    """Get available trim levels and option lists for a given brands/models selection."""
    params_hash = _params_hash(request.model_dump_json())
    cache_key = f"{_PREFIX}trims_options:{params_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: trims-and-options [%s]", params_hash)
        return TrimsAndOptionsResponse(**cached)

    sb = supabase
    try:
        resp = sb.rpc(
            "rpc_get_trims_and_options",
            {
                "p_brands": request.brands,
                "p_models": request.models,
            },
        ).execute()

        data: dict = resp.data or {}
        result = TrimsAndOptionsResponse(
            trim_levels=[OptionItem(**i) for i in data.get("trim_levels", [])],
            standard_options=[
                OptionItem(**i) for i in data.get("standard_options", [])
            ],
            paid_options=[OptionItem(**i) for i in data.get("paid_options", [])],
        )
        _redis_set(cache_key, result.model_dump(), _TTL_FILTERS)
        return result
    except Exception as e:
        logger.exception("Error calling rpc_get_trims_and_options: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch trims and options: {e}"
        )


@router.post("/scoring-search/vehicle/{vehicle_id}/refresh-derived")
def refresh_derived_features(vehicle_id: str) -> dict[str, Any]:
    """Trigger derivation of rules-based features for a given vehicle."""
    sb = supabase
    try:
        sb.rpc(
            "rpc_refresh_vehicle_features",
            {"p_vehicle_id": vehicle_id, "p_bundle_id": None},
        ).execute()

        return {"status": "success", "vehicle_id": vehicle_id}
    except Exception as e:
        logger.exception("Error calling rpc_refresh_vehicle_features: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh derived features: {e}"
        )


@router.get(
    "/scoring-search/vehicle/{vehicle_id}/similar",
    response_model=list[SimilarVehicleMatch],
)
def get_similar_vehicles(
    vehicle_id: str,
    limit: int = 5,
    duration_months: int | None = None,
    annual_mileage: int | None = None,
) -> list[SimilarVehicleMatch]:
    """Get similar vehicles sorted by best monthly price net."""
    sb = supabase
    try:
        resp = sb.rpc(
            "rpc_get_similar_vehicles",
            {
                "p_vehicle_id": vehicle_id,
                "p_limit": limit,
                "p_duration_months": duration_months,
                "p_annual_mileage": annual_mileage,
            },
        ).execute()

        if not resp.data:
            return []

        return [SimilarVehicleMatch(**row) for row in resp.data]
    except Exception as e:
        logger.exception("Error calling rpc_get_similar_vehicles: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch similar vehicles: {e}"
        )


@router.post(
    "/scoring-search/cache/batch-similar",
    response_model=SimilarBatchResponse,
)
def get_batch_similar_vehicles(req: SimilarBatchRequest) -> SimilarBatchResponse:
    """Return similar vehicles for multiple vehicle IDs in one DB query."""
    sb = supabase
    try:
        if not req.vehicle_ids:
            return SimilarBatchResponse(results={})

        response = sb.rpc(
            "rpc_get_similar_vehicles_batch",
            {
                "p_vehicle_ids": req.vehicle_ids,
                "p_limit": req.limit,
                "p_duration_months": req.duration_months,
                "p_annual_mileage": req.annual_mileage,
            },
        ).execute()

        results: dict[str, list[SimilarVehicleMatch]] = {
            vid: [] for vid in req.vehicle_ids
        }

        if response.data:
            from typing import cast, Any

            rows = cast(list[dict[str, Any]], response.data)
            for row in rows:
                source_id = str(row.pop("source_vehicle_id"))
                # Map the RPC return columns to SimilarVehicleMatch fields
                match = SimilarVehicleMatch(
                    vehicle_id=str(row.get("v_id")),
                    brand=str(row.get("brand")) if row.get("brand") else None,
                    model=str(row.get("model")) if row.get("model") else None,
                    version=str(row.get("version")) if row.get("version") else None,
                    samar_category=str(row.get("samar_category"))
                    if row.get("samar_category", row.get("v_samar"))
                    else None,
                    fuel=str(row.get("fuel"))
                    if row.get("fuel", row.get("v_fuel"))
                    else None,
                    transmission=str(row.get("transmission"))
                    if row.get("transmission", row.get("v_transmission"))
                    else None,
                    best_monthly_price=float(row.get("min_price"))
                    if row.get("min_price") is not None
                    else None,
                    image_url=str(row.get("v_image")) if row.get("v_image") else None,
                    similarity_score_pct=float(row.get("similarity_score_pct"))
                    if row.get("similarity_score_pct") is not None
                    else None,
                )

                if source_id in results:
                    results[source_id].append(match)

        return SimilarBatchResponse(results=results)
    except Exception as e:
        logger.exception("Error calling rpc_get_similar_vehicles_batch: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch batch similar vehicles: {e}"
        )


class BatchPricesRequest(BaseModel):
    vehicle_ids: List[str]
    duration_months_min: int
    duration_months_max: int
    annual_mileage_min: int
    annual_mileage_max: int
    discount_mode: str = "custom"  # 'catalog', 'offer', 'custom'
    custom_discount_pct: float = 0.0


class VehiclePrices(BaseModel):
    price_for_params: PriceForParamsResponse | None = None
    variants: List[PriceForParamsResponse] = []


class BatchPricesResponse(BaseModel):
    prices: Dict[str, VehiclePrices]


@router.post(
    "/scoring-search/cache/batch-prices",
    response_model=BatchPricesResponse,
)
def get_batch_prices(req: BatchPricesRequest) -> BatchPricesResponse:
    """Return base LTR prices (0% margin) and variants for multiple vehicles.

    Prices are returned WITHOUT margin — the frontend applies
    pricing margin via ``rawPrice / (1 - marginPct/100)``.
    """
    sb = supabase

    try:
        if not req.vehicle_ids:
            return BatchPricesResponse(prices={})

        # ── Fetch all matrix cache entries ──
        resp = (
            sb.table("vehicle_matrix_cache")
            .select(
                "vehicle_id, kalkulacja_id, duration_months, annual_mileage, monthly_price_net, tire_class, service_type, calculated_at"
            )
            .in_("vehicle_id", req.vehicle_ids)
            .limit(10000)
            .execute()
        )
        all_rows = resp.data or []

        from collections import defaultdict

        v_map: dict[str, list] = defaultdict(list)
        for r in all_rows:
            v_map[r["vehicle_id"]].append(r)

        results: dict[str, VehiclePrices] = {}

        for vid in req.vehicle_ids:
            v_prices = VehiclePrices(price_for_params=None, variants=[])
            v_rows_all = v_map.get(vid, [])

            if not v_rows_all:
                v_prices.price_for_params = PriceForParamsResponse(
                    vehicle_id=vid, found=False
                )
                results[vid] = v_prices
                continue

            # Group by kalkulacja_id for historical variants display
            calc_map: dict[str, list] = defaultdict(list)
            for r in v_rows_all:
                kid = r.get("kalkulacja_id")
                kid_str = kid if kid else ""
                calc_map[kid_str].append(r)

            # Keep only the newest calculation per (duration, mileage) combo
            param_map: dict[tuple, tuple] = {}
            for r in v_rows_all:
                key = (r.get("duration_months"), r.get("annual_mileage"))
                if not key[0] or not key[1]:
                    continue
                dt = None
                if r.get("calculated_at"):
                    dt = datetime.fromisoformat(
                        r["calculated_at"].replace("Z", "+00:00")
                    )
                if key not in param_map:
                    param_map[key] = (dt, r)
                else:
                    existing_dt = param_map[key][0]
                    if dt and (not existing_dt or dt > existing_dt):
                        param_map[key] = (dt, r)

            latest_rows = [p[1] for p in param_map.values()]
            if not latest_rows:
                v_prices.price_for_params = PriceForParamsResponse(
                    vehicle_id=vid, found=False
                )
                results[vid] = v_prices
                continue

            variants_count = len(latest_rows)

            def is_in_bounds(r: dict) -> bool:
                return (
                    req.duration_months_min
                    <= r["duration_months"]
                    <= req.duration_months_max
                    and req.annual_mileage_min
                    <= r["annual_mileage"]
                    <= req.annual_mileage_max
                )

            valid_rows = [r for r in latest_rows if is_in_bounds(r)]

            if not valid_rows:
                v_prices.price_for_params = PriceForParamsResponse(
                    vehicle_id=vid, found=False
                )
                results[vid] = v_prices
                continue

            best_match = min(
                valid_rows,
                key=lambda x: float(x.get("monthly_price_net") or float("inf")),
            )

            # Return raw cache price — no margin applied
            display_price = float(best_match["monthly_price_net"] or 0)

            v_prices.price_for_params = PriceForParamsResponse(
                vehicle_id=vid,
                duration_months=best_match["duration_months"],
                annual_mileage=best_match["annual_mileage"],
                monthly_price_net=round(display_price, 2),
                calculated_at=best_match.get("calculated_at"),
                found=True,
                variants_count=variants_count,
                tire_class=best_match.get("tire_class"),
                service_type=best_match.get("service_type"),
                kalkulacja_id=best_match.get("kalkulacja_id"),
            )

            # ── Variants (other kalkulacja_ids) ──
            variant_responses: list[PriceForParamsResponse] = []
            main_kid = best_match.get("kalkulacja_id")

            for kid, rows in calc_map.items():
                if kid == main_kid:
                    continue

                valid_kid_rows = [r for r in rows if is_in_bounds(r)]
                kid_match = None
                if valid_kid_rows:
                    kid_match = min(
                        valid_kid_rows,
                        key=lambda x: float(x.get("monthly_price_net") or float("inf")),
                    )

                if kid_match:
                    # Return raw cache price — no margin applied
                    v_price = (
                        round(
                            float(kid_match["monthly_price_net"]),
                            2,
                        )
                        if kid_match.get("monthly_price_net")
                        else 0.0
                    )

                    variant_responses.append(
                        PriceForParamsResponse(
                            vehicle_id=vid,
                            duration_months=kid_match["duration_months"],
                            annual_mileage=kid_match["annual_mileage"],
                            monthly_price_net=round(v_price, 2),
                            calculated_at=kid_match.get("calculated_at"),
                            found=True,
                            variants_count=variants_count,
                            tire_class=kid_match.get("tire_class"),
                            service_type=kid_match.get("service_type"),
                            kalkulacja_id=kid_match.get("kalkulacja_id"),
                        )
                    )

            variant_responses.sort(key=lambda x: x.calculated_at or "", reverse=True)
            v_prices.variants = variant_responses
            results[vid] = v_prices

        return BatchPricesResponse(prices=results)
    except Exception as e:
        logger.exception("Error in get_batch_prices: %s", e)
        raise HTTPException(status_code=500, detail=f"Batch prices failed: {e}")


@router.get(
    "/scoring-search/vehicle/{vehicle_id}/price-for-params",
    response_model=PriceForParamsResponse,
)
def get_price_for_params(
    vehicle_id: str,
    duration_months: int,
    annual_mileage: int,
    margin: float = 0.0,
    discount_mode: str = "catalog",
    custom_discount_pct: float = 0.0,
) -> PriceForParamsResponse:
    """Return the LTR price tile based exclusively on historical cache."""
    sb = supabase
    try:
        resp = (
            sb.table("vehicle_matrix_cache")
            .select(
                "duration_months, annual_mileage, monthly_price_net, calculated_at, kalkulacja_id, tire_class, service_type"
            )
            .eq("vehicle_id", vehicle_id)
            .execute()
        )
        rows_all = resp.data or []

        if not rows_all:
            return PriceForParamsResponse(vehicle_id=vehicle_id, found=False)

        from collections import defaultdict

        # Group by kalkulacja_id to find the latest
        calc_map = defaultdict(list)
        kalk_times = {}
        for r in rows_all:
            kid = r.get("kalkulacja_id")
            kid_str = kid if kid else ""
            calc_map[kid_str].append(r)
            if r.get("calculated_at"):
                dt = datetime.fromisoformat(r["calculated_at"].replace("Z", "+00:00"))
                if kid_str not in kalk_times or dt > kalk_times[kid_str]:
                    kalk_times[kid_str] = dt

        # Find the latest kalkulacja_id
        latest_kid = None
        if kalk_times:
            latest_kid = max(kalk_times, key=kalk_times.get)
        else:
            latest_kid = list(calc_map.keys())[0]

        variants_count = len(calc_map)
        latest_rows = calc_map[latest_kid]

        # Exact match logic
        exact_match = next(
            (
                r
                for r in latest_rows
                if r["duration_months"] == duration_months
                and r["annual_mileage"] == annual_mileage
            ),
            None,
        )

        best_match = exact_match
        if not best_match:
            return PriceForParamsResponse(vehicle_id=vehicle_id, found=False)

        base_price_best = (
            float(best_match["monthly_price_net"])
            if best_match["monthly_price_net"]
            else 0.0
        )
        display_price_best = base_price_best / (1.0 - (margin / 100.0))

        return PriceForParamsResponse(
            vehicle_id=vehicle_id,
            duration_months=best_match["duration_months"],
            annual_mileage=best_match["annual_mileage"],
            monthly_price_net=round(display_price_best, 2),
            calculated_at=best_match.get("calculated_at"),
            found=True,
            variants_count=variants_count,
            tire_class=best_match.get("tire_class"),
            service_type=best_match.get("service_type"),
            kalkulacja_id=best_match.get("kalkulacja_id"),
        )
    except Exception as e:
        logger.exception("Error in get_price_for_params [%s]: %s", vehicle_id, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch price for params: {e}"
        )


@router.get(
    "/scoring-search/vehicle/{vehicle_id}/price-variants",
    response_model=list[PriceForParamsResponse],
)
def get_price_variants(
    vehicle_id: str,
    annual_mileage: int,
) -> list[PriceForParamsResponse]:
    """Return the LTR price variants for all standard durations at a given annual mileage."""
    sb = supabase
    try:
        resp = (
            sb.table("vehicle_matrix_cache")
            .select("duration_months, annual_mileage, monthly_price_net")
            .eq("vehicle_id", vehicle_id)
            .eq("annual_mileage", annual_mileage)
            .in_("duration_months", [24, 36, 48, 60])
            .execute()
        )
        rows = resp.data or []

        grouped_variants = {}
        for row in rows:
            if row.get("monthly_price_net"):
                dur = row["duration_months"]
                price = float(row["monthly_price_net"])
                if (
                    dur not in grouped_variants
                    or price < grouped_variants[dur]["monthly_price_net"]
                ):
                    grouped_variants[dur] = {
                        "duration_months": dur,
                        "annual_mileage": row["annual_mileage"],
                        "monthly_price_net": price,
                    }

        variants = [
            PriceForParamsResponse(
                vehicle_id=vehicle_id,
                duration_months=v["duration_months"],
                annual_mileage=v["annual_mileage"],
                monthly_price_net=v["monthly_price_net"],
                found=True,
            )
            for v in grouped_variants.values()
        ]

        # Sort variants by duration_months ascending
        variants.sort(key=lambda x: x.duration_months or 0)
        return variants
    except Exception as e:
        logger.exception("Error in get_price_variants [%s]: %s", vehicle_id, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch price variants: {e}"
        )


# ── Cache management ──────────────────────────────────────────────────────────


@router.get("/scoring-search/cache/stats")
def get_search_cache_stats() -> dict[str, Any]:
    """Zwraca statystyki Redis (dostępność, liczba kluczy, pamięć)."""
    return get_cache_stats()


@router.get("/scoring-search/readiness-check")
def readiness_check() -> dict[str, Any]:
    """Return per-vehicle cache/readiness status with missing field details."""
    sb = supabase
    try:
        v_res = (
            sb.table("vehicle_synthesis")
            .select("id, brand, model, verification_status, synthesis_data")
            .neq("verification_status", "moved_to_library")
            .execute()
        )
        vehicles = v_res.data or []

        c_res = sb.table("vehicle_matrix_cache").select("vehicle_id").execute()
        cached_ids = set(row["vehicle_id"] for row in (c_res.data or []))

        result_vehicles: list[dict[str, Any]] = []
        cached_count = 0
        calculable_count = 0
        failed_count = 0

        for v in vehicles:
            vid = v["id"]
            brand = v.get("brand") or "?"
            model = v.get("model") or "?"
            status = v.get("verification_status") or "?"
            has_cache = vid in cached_ids
            missing: list[str] = []

            sd = v.get("synthesis_data") or {}
            cs = sd.get("card_summary") or {}
            mai = sd.get("mapped_ai_data") or {}

            parsed_prices = cs.get("parsed_prices") or {}
            base_price = (
                cs.get("base_price")
                or parsed_prices.get("base")
                or sd.get("universal_features", {}).get("cena_pojazdu")
            )
            if not base_price:
                missing.append("base_price")

            power_kw = cs.get("power_kw") or 0
            powertrain = cs.get("powertrain", "") or ""
            if not power_kw and not powertrain:
                missing.append("power_kw")

            samar = cs.get("samar_category") or mai.get("samar_category")
            if not samar:
                missing.append("samar_category")

            engine = cs.get("engine_category") or mai.get("fuel")
            if not engine:
                missing.append("engine_category")

            can_calculate = len(missing) == 0
            if has_cache:
                cached_count += 1
            if can_calculate:
                calculable_count += 1
            else:
                failed_count += 1

            result_vehicles.append(
                {
                    "vehicle_id": vid,
                    "brand": brand,
                    "model": model,
                    "status": status,
                    "has_cache": has_cache,
                    "can_calculate": can_calculate,
                    "missing_fields": missing,
                }
            )

        return {
            "total": len(vehicles),
            "cached": cached_count,
            "calculable": calculable_count,
            "failed": failed_count,
            "vehicles": result_vehicles,
        }
    except Exception as e:
        logger.exception("Error in readiness_check: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring-search/cache/progress/{job_id}")
def get_cache_job_progress(job_id: str) -> dict[str, Any]:
    """Zwraca aktualny progress przeliczania cache dla danego job_id z Celery."""
    task = AsyncResult(job_id, app=celery_app)

    if task.state == "SUCCESS":
        return {"status": "done", "result": task.result}
    elif task.state == "FAILURE":
        return {"status": "error", "error": str(task.info)}
    elif task.state in ["PENDING", "STARTED", "RETRY"]:
        return {"status": "pending", "state": task.state}
    else:
        return {"status": "unknown", "state": task.state}
