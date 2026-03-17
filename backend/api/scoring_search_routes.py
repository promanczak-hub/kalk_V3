"""FastAPI routes for the reverse_search scoring engine."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.database import supabase
from core.matrix_cache_job import (
    async_refresh_matrix_cache,
    get_cache_progress,
)
from core.models_scoring_search import (
    AvailableFiltersRequest,
    ScoringSearchRequest,
    ScoringSearchResponse,
    ScoringSearchMatch,
    InitialDataResponse,
    SimilarVehicleMatch,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring_search"])

@router.post("/scoring-search/available-filters")
def get_available_filters(request: AvailableFiltersRequest) -> dict[str, Any]:
    """Get dynamic facets (enums, ranges) generated directly from DB evidence."""
    sb = supabase
    try:
        resp = sb.rpc(
            "rpc_get_available_filters",
            {
                "p_brands": request.brands,
                "p_models": request.models,
                "p_samar_class_ids": request.samar_class_ids,
                "p_current_filters": request.current_filters or {}
            }
        ).execute()

        if not resp.data:
            return {}

        return resp.data
    except Exception as e:
        logger.exception(f"Error calling rpc_get_available_filters: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch available filters: {e}"
        )

@router.post("/scoring-search/search")
def run_scoring_search(request: ScoringSearchRequest) -> ScoringSearchResponse:
    """Run search scoring against Must-Have and Nice-To-Have criteria."""
    sb = supabase
    try:
        req_list = [req.model_dump() for req in request.requirements]
        
        # Add support when values lists are required for "in" operator
        for req in req_list:
            if req.get("operator") == "in" and req.get("values"):
                req["values"] = req["values"]

        resp = sb.rpc(
            "rpc_reverse_search",
            {
                "p_brands": request.brands,
                "p_models": request.models,
                "p_samar_class_ids": request.samar_class_ids,
                "p_requirements": req_list
            }
        ).execute()

        matches = []
        for row in resp.data:
            matches.append(ScoringSearchMatch(**row))

        # Paginate
        page_results = matches[request.offset:request.offset + request.limit]

        return ScoringSearchResponse(
            results=page_results,
            total_count=len(matches)
        )
    except Exception as e:
        logger.exception(f"Error calling rpc_reverse_search: {e}")
        raise HTTPException(
            status_code=500, detail=f"Search failed: {e}"
        )

@router.get("/scoring-search/initial-data", response_model=InitialDataResponse)
def get_initial_data() -> InitialDataResponse:
    """Get unique brands, models, and Samar classes for the Multi-Filter UI."""
    sb = supabase
    try:
        resp = sb.rpc("rpc_get_scoring_initial_data").execute()
        return InitialDataResponse(**resp.data)
    except Exception as e:
        logger.exception(f"Error calling rpc_get_scoring_initial_data: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch initial data: {e}"
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
        logger.exception(f"Error calling rpc_refresh_vehicle_features: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh derived features: {e}"
        )

@router.get("/scoring-search/vehicle/{vehicle_id}/similar", response_model=list[SimilarVehicleMatch])
def get_similar_vehicles(vehicle_id: str, limit: int = 5) -> list[SimilarVehicleMatch]:
    """Get similar vehicles sorted by best monthly price net."""
    sb = supabase
    try:
        resp = sb.rpc(
            "rpc_get_similar_vehicles",
            {
                "p_vehicle_id": vehicle_id,
                "p_limit": limit
            }
        ).execute()

        if not resp.data:
            return []

        return [SimilarVehicleMatch(**row) for row in resp.data]
    except Exception as e:
        logger.exception(f"Error calling rpc_get_similar_vehicles: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch similar vehicles: {e}"
        )

class RefreshCacheRequest(BaseModel):
    vehicle_ids: list[str]

@router.post("/scoring-search/cache/refresh-matrix")
def trigger_matrix_cache_refresh(
    req: RefreshCacheRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Uruchamia asynchroniczne przeliczanie matrycy LTR z job tracking."""
    if not req.vehicle_ids:
        raise HTTPException(
            status_code=400, detail="vehicle_ids list cannot be empty"
        )

    job_id = str(uuid.uuid4())
    chunk_size = 20
    for i in range(0, len(req.vehicle_ids), chunk_size):
        chunk = req.vehicle_ids[i : i + chunk_size]
        background_tasks.add_task(async_refresh_matrix_cache, chunk, job_id)

    return {
        "status": "success",
        "job_id": job_id,
        "message": (
            f"Rozpoczęto weryfikację i zapis cache "
            f"dla {len(req.vehicle_ids)} pojazdów w tle."
        ),
    }

@router.post("/scoring-search/cache/refresh-missing")
def trigger_matrix_cache_refresh_missing(
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Przeliczanie matrycy LTR TYLKO dla aut bez cache, z job tracking."""
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
        chunk_size = 20
        for i in range(0, len(missing_ids), chunk_size):
            chunk = missing_ids[i : i + chunk_size]
            background_tasks.add_task(
                async_refresh_matrix_cache, chunk, job_id
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
        logger.exception(f"Error triggering missing cache refresh: {e}")
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

            # Check base_price
            parsed_prices = cs.get("parsed_prices") or {}
            base_price = (
                cs.get("base_price")
                or parsed_prices.get("base")
                or sd.get("universal_features", {}).get("cena_pojazdu")
            )
            if not base_price:
                missing.append("base_price")

            # Check power
            power_kw = cs.get("power_kw") or 0
            powertrain = cs.get("powertrain", "") or ""
            if not power_kw and not powertrain:
                missing.append("power_kw")

            # Check SAMAR class
            samar = cs.get("samar_category") or mai.get("samar_category")
            if not samar:
                missing.append("samar_category")

            # Check engine
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
        logger.exception(f"Error in readiness_check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring-search/cache/progress/{job_id}")
def get_cache_job_progress(job_id: str) -> dict[str, Any]:
    """Zwraca aktualny progress przeliczania cache dla danego job_id."""
    progress = get_cache_progress(job_id)
    if progress is None:
        return {
            "status": "unknown",
            "message": "Job nie znaleziony — jeszcze nie wystartował lub wygasł.",
        }
    return progress
