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
