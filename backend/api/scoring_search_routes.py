"""FastAPI routes for the reverse_search scoring engine."""

import hashlib
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult

from core.database import supabase
from core.matrix_cache_job import calculate_live_ltr_tile
from core.celery_app import celery_app
from tasks.matrix_tasks import process_matrix_refresh_task
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
)
from core.redis_cache import (
    _get_client,
    _PREFIX,
    cache_invalidate_pattern,
    get_cache_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring_search"])

# ── TTL constants ──────────────────────────────────────────────────────────────
_TTL_INITIAL_DATA = 3600   # 1 hour  — changes only when vehicles are added
_TTL_FILTERS = 300         # 5 min   — depends on vehicle DB state
_TTL_SEARCH = 120          # 2 min   — user results; short enough to stay fresh


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
        logger.debug("Redis SET error [%s]: %s", key, exc)


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
                "p_current_filters": request.current_filters or {}
            }
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
        page_results = matches[request.offset:request.offset + request.limit]
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
                "p_requirements": req_list
            }
        ).execute()

        all_matches = [ScoringSearchMatch(**row) for row in resp.data]

        # Cache all raw results (pagination applied after cache read)
        _redis_set(
            cache_key,
            {"results_raw": resp.data, "total": len(all_matches)},
            _TTL_SEARCH,
        )

        page_results = all_matches[request.offset:request.offset + request.limit]
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


@router.post("/scoring-search/trims-and-options", response_model=TrimsAndOptionsResponse)
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
            standard_options=[OptionItem(**i) for i in data.get("standard_options", [])],
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
            {
                "p_vehicle_id": vehicle_id,
                "p_bundle_id": None
            }
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
                "p_annual_mileage": annual_mileage
            }
        ).execute()

        if not resp.data:
            return []

        return [SimilarVehicleMatch(**row) for row in resp.data]
    except Exception as e:
        logger.exception("Error calling rpc_get_similar_vehicles: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch similar vehicles: {e}"
        )


@router.get(
    "/scoring-search/vehicle/{vehicle_id}/price-for-params",
    response_model=PriceForParamsResponse,
)
def get_price_for_params(
    vehicle_id: str,
    duration_months: int,
    annual_mileage: int,
) -> PriceForParamsResponse:
    """Return the LTR price tile closest to the requested duration/mileage."""
    sb = supabase
    try:
        resp = (
            sb.table("vehicle_matrix_cache")
            .select("duration_months, annual_mileage, monthly_price_net")
            .eq("vehicle_id", vehicle_id)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return PriceForParamsResponse(vehicle_id=vehicle_id, found=False)

        # 1. Sprawdzenie czy jest exact match w BD
        exact_match = next(
            (r for r in rows if r["duration_months"] == duration_months and r["annual_mileage"] == annual_mileage),
            None
        )
        if exact_match:
            return PriceForParamsResponse(
                vehicle_id=vehicle_id,
                duration_months=duration_months,
                annual_mileage=annual_mileage,
                monthly_price_net=float(exact_match["monthly_price_net"]) if exact_match["monthly_price_net"] else None,
                found=True,
            )

        # 2. Sprawdzenie szybkiego cache'a Redisa na live (on-demand) tile
        live_cache_key = f"ltr:live:{vehicle_id}:{duration_months}:{annual_mileage}"
        cached_live = _redis_get(live_cache_key)
        if cached_live is not None:
            return PriceForParamsResponse(
                vehicle_id=vehicle_id,
                duration_months=duration_months,
                annual_mileage=annual_mileage,
                monthly_price_net=float(cached_live),
                found=True,
            )

        # 3. Wyliczenie live w ok. ~50ms
        live_price = calculate_live_ltr_tile(vehicle_id, duration_months, annual_mileage)
        if live_price is not None:
            _redis_set(live_cache_key, live_price, 86400) # Zapis do Redisa na 24h
            return PriceForParamsResponse(
                vehicle_id=vehicle_id,
                duration_months=duration_months,
                annual_mileage=annual_mileage,
                monthly_price_net=live_price,
                found=True,
            )

        # 4. Fallback: Jeśli nawet live script zawiedzie z powodu braku konfiguracji
        # pokazujemy najbliższy tile. Na froncie isExactMatch == false -> wygeneruje gwiazdkę.
        def distance(row: dict) -> float:
            dm_diff = abs(row["duration_months"] - duration_months)
            km_diff = abs(row["annual_mileage"] - annual_mileage)
            # Normalize: 1 month ≈ 10k km difference in weight
            return dm_diff * 10_000 + km_diff

        best = min(rows, key=distance)
        return PriceForParamsResponse(
            vehicle_id=vehicle_id,
            duration_months=best["duration_months"],
            annual_mileage=best["annual_mileage"],
            monthly_price_net=float(best["monthly_price_net"]) if best["monthly_price_net"] else None,
            found=True,
        )
    except Exception as e:
        logger.exception("Error in get_price_for_params [%s]: %s", vehicle_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch price for params: {e}")


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
                if dur not in grouped_variants or price < grouped_variants[dur]["monthly_price_net"]:
                    grouped_variants[dur] = {
                        "duration_months": dur,
                        "annual_mileage": row["annual_mileage"],
                        "monthly_price_net": price
                    }
        
        variants = [
            PriceForParamsResponse(
                vehicle_id=vehicle_id,
                duration_months=v["duration_months"],
                annual_mileage=v["annual_mileage"],
                monthly_price_net=v["monthly_price_net"],
                found=True,
            ) for v in grouped_variants.values()
        ]
        
        # Sort variants by duration_months ascending
        variants.sort(key=lambda x: x.duration_months or 0)
        return variants
    except Exception as e:
        logger.exception("Error in get_price_variants [%s]: %s", vehicle_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch price variants: {e}")



# ── Cache management ──────────────────────────────────────────────────────────

@router.get("/scoring-search/cache/stats")
def get_search_cache_stats() -> dict[str, Any]:
    """Zwraca statystyki Redis (dostępność, liczba kluczy, pamięć)."""
    return get_cache_stats()


@router.delete("/scoring-search/cache/invalidate")
def invalidate_search_cache() -> dict[str, Any]:
    """Ręczny flush kluczy search, filters i initial_data z Redis."""
    deleted = 0
    deleted += cache_invalidate_pattern("search:*")
    deleted += cache_invalidate_pattern("filters:*")
    deleted += cache_invalidate_pattern("initial_data")
    return {
        "status": "ok",
        "deleted_keys": deleted,
        "message": f"Usunięto {deleted} kluczy z Redis.",
    }


# ── Matrix cache management ───────────────────────────────────────────────────

class RefreshCacheRequest(BaseModel):
    vehicle_ids: list[str]


@router.post("/scoring-search/cache/refresh-matrix")
def trigger_matrix_cache_refresh(
    req: RefreshCacheRequest,
) -> dict[str, Any]:
    """Uruchamia asynchroniczne przeliczanie matrycy LTR za pomocą Celery."""
    if not req.vehicle_ids:
        raise HTTPException(
            status_code=400, detail="vehicle_ids list cannot be empty"
        )

    # Use first vehicle ID to generate a predictable or random job_id
    job_id = str(uuid.uuid4())
    
    # We submit the whole list to a single Celery task.
    # Celery handles lists well. To keep the frontend simple, we return one job_id.
    process_matrix_refresh_task.apply_async(
        args=[req.vehicle_ids, job_id], 
        task_id=job_id
    )

    return {
        "status": "success",
        "job_id": job_id,
        "message": (
            f"Rozpoczęto weryfikację i zapis cache "
            f"dla {len(req.vehicle_ids)} pojazdów w tle Celery."
        ),
    }


@router.post("/scoring-search/cache/refresh-missing")
def trigger_matrix_cache_refresh_missing() -> dict[str, Any]:
    """Przeliczanie matrycy LTR TYLKO dla aut bez cache za pomocą Celery."""
    sb = supabase
    try:
        res_all = sb.table("vehicle_synthesis").select("id").execute()
        all_ids = set(row["id"] for row in (res_all.data or []))

        res_cache = (
            sb.table("vehicle_matrix_cache").select("vehicle_id").execute()
        )
        cached_ids = set(
            row["vehicle_id"] for row in (res_cache.data or [])
        )

        missing_ids = list(all_ids - cached_ids)

        if not missing_ids:
            return {
                "status": "success",
                "message": "Wszystkie pojazdy posiadają już przeliczony cache.",
                "job_id": None,
            }

        job_id = str(uuid.uuid4())
        process_matrix_refresh_task.apply_async(
            args=[missing_ids, job_id], 
            task_id=job_id
        )

        return {
            "status": "success",
            "job_id": job_id,
            "message": (
                f"Rozpoczęto przeliczanie cache "
                f"dla {len(missing_ids)} brakujących pojazdów."
            ),
            "missing_count": len(missing_ids),
        }
    except Exception as e:
        logger.exception("Error triggering missing cache refresh: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Wystąpił błąd: {e}"
        )


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

            result_vehicles.append({
                "vehicle_id": vid,
                "brand": brand,
                "model": model,
                "status": status,
                "has_cache": has_cache,
                "can_calculate": can_calculate,
                "missing_fields": missing,
            })

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
    
    if task.state == 'SUCCESS':
        return {"status": "done", "result": task.result}
    elif task.state == 'FAILURE':
        return {"status": "error", "error": str(task.info)}
    elif task.state in ['PENDING', 'STARTED', 'RETRY']:
        return {"status": "pending", "state": task.state}
    else:
        return {"status": "unknown", "state": task.state}
