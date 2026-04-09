"""FastAPI routes for the reverse_search scoring engine."""

import hashlib
import json
import logging

from datetime import datetime
import time
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
    SimilarityReasons,
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
from core.embeddings import generate_embedding

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


def _supabase_execute_with_retry(query_obj: Any, max_retries: int = 3) -> Any:
    """Execute a Supabase query resolving known httpx 'Server disconnected' or timeout issues."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return query_obj.execute()
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            if (
                "server disconnected" in err_str
                or "unreachable" in err_str
                or "timeout" in err_str
                or "connection" in err_str
            ):
                logger.warning(
                    "Supabase connection issue (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    e,
                )
                time.sleep(0.5 * (2**attempt))
                continue
            raise e
    raise last_exc


def _build_similar_vehicle_match(row: dict[str, Any]) -> SimilarVehicleMatch:
    """Build a SimilarVehicleMatch from a raw RPC row dict.

    Handles both single and batch RPC variants (some field names differ),
    and maps the similarity_reasons JSONB payload to the SimilarityReasons model.
    """
    raw_reasons = row.get("similarity_reasons")
    similarity_reasons: SimilarityReasons | None = None
    if isinstance(raw_reasons, dict):
        similarity_reasons = SimilarityReasons(
            samar_match=bool(raw_reasons.get("samar_match", False)),
            body_match=bool(raw_reasons.get("body_match", False)),
            fuel_match=bool(raw_reasons.get("fuel_match", False)),
            drive_match=bool(raw_reasons.get("drive_match", False)),
            equipment_match=bool(raw_reasons.get("equipment_match", False)),
            is_same_brand=bool(raw_reasons.get("is_same_brand", False)),
            equipment_similarity_pct=float(raw_reasons["equipment_similarity_pct"])
            if raw_reasons.get("equipment_similarity_pct") is not None
            else None,
            price_pct_diff=float(raw_reasons["price_pct_diff"])
            if raw_reasons.get("price_pct_diff") is not None
            else None,
            samar_category=raw_reasons.get("samar_category"),
            body_style=raw_reasons.get("body_style"),
            base_price=float(raw_reasons["base_price"])
            if raw_reasons.get("base_price") is not None
            else None,
            paid_options=raw_reasons.get("paid_options"),
        )

    return SimilarVehicleMatch(
        vehicle_id=str(row.get("vehicle_id") or row.get("v_id", "")),
        brand=row.get("brand"),
        model=row.get("model"),
        version=row.get("version"),
        samar_category=str(row.get("samar_category") or row.get("v_samar") or "N/A"),
        fuel=str(row.get("fuel") or row.get("v_fuel") or "N/A"),
        transmission=str(row.get("transmission") or row.get("v_transmission") or "N/A"),
        best_monthly_price=float(
            row.get("best_monthly_price") or row.get("min_price") or 0
        ),
        image_url=str(row.get("image_url") or row.get("v_image") or ""),
        similarity_score_pct=float(row.get("similarity_score_pct") or 0),
        power_hp=int(row.get("power_hp") or 0),
        body_style=str(row.get("body_style") or "N/A"),
        vehicle_class=str(row.get("vehicle_class") or "N/A"),
        drive_type=str(row.get("drive_type") or "N/A"),
        similarity_reasons=similarity_reasons,
    )


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

        semantic_vector = None
        if request.semantic_query:
            logger.info(
                "Generating embedding for semantic query: '%s'", request.semantic_query
            )
            semantic_vector = generate_embedding(request.semantic_query)
            if semantic_vector is None:
                logger.warning(
                    "Failed to generate embedding for query: '%s'",
                    request.semantic_query,
                )

        resp = sb.rpc(
            "rpc_reverse_search",
            {
                "p_brands": request.brands,
                "p_models": request.models,
                "p_samar_class_ids": request.samar_class_ids,
                "p_trims": request.trims,
                "p_vehicle_ids": request.vehicle_ids,
                "p_requirements": req_list,
                "p_semantic_query_vector": semantic_vector,
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
    mode: str = "rule-based",
) -> list[SimilarVehicleMatch]:
    """Get similar vehicles sorted by best monthly price net. Supports 'rule-based' (default) and 'semantic' modes."""
    sb = supabase
    method = (
        "rpc_get_similar_vehicles_semantic"
        if mode == "semantic"
        else "rpc_get_similar_vehicles"
    )

    try:
        resp = _supabase_execute_with_retry(
            sb.rpc(
                method,
                {
                    "p_vehicle_id": vehicle_id,
                    "p_limit": limit,
                    "p_duration_months": duration_months,
                    "p_annual_mileage": annual_mileage,
                },
            )
        )

        if not resp.data:
            return []

        return [_build_similar_vehicle_match(row) for row in resp.data]
    except Exception as e:
        logger.exception("Error calling %s: %s", method, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch similar vehicles: {e}"
        )


class AlternativesRequest(BaseModel):
    category: str
    limit: int = 5
    duration_months: int | None = None
    annual_mileage: int | None = None
    requirements: List[Any] = []

@router.post(
    "/scoring-search/vehicle/{vehicle_id}/alternatives",
    response_model=list[SimilarVehicleMatch],
)
def get_vehicle_alternatives(
    vehicle_id: str,
    request: AlternativesRequest
) -> list[SimilarVehicleMatch]:
    """Get alternative vehicles based on synthetic semantic queries."""
    sb = supabase
    try:
        synthetic_queries = {
            "cheaper": "Budget friendly, affordable, economical, low cost of ownership, high value for money, cheap to maintain, basic standard.",
            "stronger": "High performance, powerful engine, fast acceleration, sporty driving, huge horsepower, high torque, dynamic.",
            "greener": "Eco-friendly, full electric, plug-in hybrid, low emissions, green energy, sustainable, low fuel consumption.",
            "safer": "Advanced safety systems, highest NCAP rating, multiple airbags, collision avoidance, blind spot monitoring, lane keep assist, robust structure.",
            "more_comfortable": "Premium comfort, smooth suspension, quiet cabin, ergonomic seats, massage function, luxury interior materials, dual zone climate control, ample legroom.",
        }

        if request.category not in synthetic_queries:
            raise HTTPException(status_code=400, detail=f"Unknown category: {request.category}")

        synthetic_query = synthetic_queries[request.category]
        logger.info(
            "Generating embedding for synthetic query: '%s' (category: %s)",
            synthetic_query,
            request.category,
        )
        synthetic_vector = generate_embedding(synthetic_query)

        if not synthetic_vector:
            raise ValueError("Failed to generate embedding for synthetic concept.")

        # Fetch more to allow filtering
        limit_to_fetch = request.limit * 5 if request.requirements else request.limit
        
        resp = _supabase_execute_with_retry(
            sb.rpc(
                "rpc_get_alternatives_semantic",
                {
                    "p_vehicle_id": vehicle_id,
                    "p_synthetic_vector": synthetic_vector,
                    "p_limit": limit_to_fetch,
                    "p_duration_months": request.duration_months,
                    "p_annual_mileage": request.annual_mileage,
                },
            )
        )
        candidates = resp.data or []
        
        must_haves = [req for req in request.requirements if isinstance(req, dict) and req.get("requirement") == "MUST_HAVE"]
        
        if not must_haves:
            return [
                _build_similar_vehicle_match(row["similarity_json"])
                for row in candidates[:request.limit]
            ]
            
        candidate_ids = [row["similarity_json"]["vehicle_id"] for row in candidates if "similarity_json" in row]
        if not candidate_ids:
            return []
            
        # 1. Fetch synthesis data for options check
        synthesis_resp = _supabase_execute_with_retry(
            sb.table("vehicle_synthesis").select("id, synthesis_data").in_("id", candidate_ids)
        )
        synthesis_map = {row["id"]: row["synthesis_data"] for row in (synthesis_resp.data or [])}
        
        # 2. Fetch features directly using REST URL override to hit reverse_search schema
        features_resp = _supabase_execute_with_retry(
            sb.schema("reverse_search").table("vehicle_features_summary_view").select(
                "source_vehicle_id, feature_key, resolved_value_bool, resolved_value_text, resolved_value_num"
            ).in_("source_vehicle_id", candidate_ids)
        )
            
        features_map = {}
        for row in (features_resp.data or []):
            vid = row["source_vehicle_id"]
            if vid not in features_map:
                features_map[vid] = {}
            features_map[vid][row["feature_key"]] = row
            
        # Filter logic
        filtered_results = []
        for row in candidates:
            sim_json = row["similarity_json"]
            vid = sim_json["vehicle_id"]
            ok = True
            
            for req in must_haves:
                fkey = req.get("feature_key")
                op = req.get("operator")
                val = req.get("value")
                
                if fkey in ('dummy', 'duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net'):
                    continue
                    
                match = False
                if str(fkey).startswith("opt_std:"):
                    opt_name = fkey[8:]
                    std_opts = synthesis_map.get(vid, {}).get("card_summary", {}).get("standard_equipment", [])
                    if opt_name in std_opts:
                        match = True
                elif str(fkey).startswith("opt_paid:"):
                    opt_name = fkey[9:]
                    paid_opts = synthesis_map.get(vid, {}).get("card_summary", {}).get("paid_options", [])
                    if any(po.get("name") == opt_name for po in paid_opts):
                        match = True
                else:
                    feat = features_map.get(vid, {}).get(fkey, {})
                    if op == "eq":
                        if str(val).lower() == "true":
                            match = feat.get("resolved_value_bool") is True
                        elif str(val).lower() == "false":
                            match = not feat.get("resolved_value_bool")
                        else:
                            match = str(feat.get("resolved_value_text")) == str(val)
                    elif op in ("gte", "lte"):
                        v_num = feat.get("resolved_value_num")
                        if v_num is not None:
                            try:
                                num = float(val)
                                if op == "gte":
                                    match = v_num >= num
                                else:
                                    match = v_num <= num
                            except (ValueError, TypeError):
                                pass
                    elif op == "in" and isinstance(val, list):
                        match = feat.get("resolved_value_text") in val
                
                if not match:
                    ok = False
                    break
                    
            if ok:
                filtered_results.append(_build_similar_vehicle_match(sim_json))
                if len(filtered_results) >= request.limit:
                    break
                    
        return filtered_results

    except Exception as e:
        logger.exception("Error calling alternatives for category %s: %s", request.category, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch alternatives: {e}"
        )


@router.post(
    "/scoring-search/cache/batch-similar",
    response_model=SimilarBatchResponse,
)
def get_batch_similar_vehicles(req: SimilarBatchRequest) -> SimilarBatchResponse:
    """Return similar vehicles for multiple vehicle IDs in one DB query. Supports 'rule-based' and 'semantic'."""
    sb = supabase
    method = (
        "rpc_get_similar_vehicles_batch_semantic"
        if req.mode == "semantic"
        else "rpc_get_similar_vehicles_batch"
    )

    try:
        if not req.vehicle_ids:
            return SimilarBatchResponse(results={})

        response = _supabase_execute_with_retry(
            sb.rpc(
                method,
                {
                    "p_vehicle_ids": req.vehicle_ids,
                    "p_limit": req.limit,
                    "p_duration_months": req.duration_months,
                    "p_annual_mileage": req.annual_mileage,
                    "p_requirements": [r.model_dump() for r in req.requirements]
                    if req.requirements
                    else [],
                },
            )
        )

        results: dict[str, list[SimilarVehicleMatch]] = {
            vid: [] for vid in req.vehicle_ids
        }

        if response.data:
            from typing import cast, Any

            rows = cast(list[dict[str, Any]], response.data)
            for row in rows:
                source_id = str(row.pop("source_vehicle_id"))
                match = _build_similar_vehicle_match(row)
                if source_id in results:
                    results[source_id].append(match)

        return SimilarBatchResponse(results=results)
    except Exception as e:
        logger.exception("Error calling %s: %s", method, e)
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
    Uses rpc_get_batch_prices to avoid PostgREST 1000-row limit.
    """
    sb = supabase

    try:
        if not req.vehicle_ids:
            return BatchPricesResponse(prices={})

        # ── Call RPC for batch prices ──
        # This function identifies the best match per vehicle ID within duration/mileage bounds
        # and returns total variants count, solving the 1000-row limit issue.
        resp = _supabase_execute_with_retry(
            sb.rpc(
                "rpc_get_batch_prices",
                {
                    "p_vehicle_ids": req.vehicle_ids,
                    "p_duration_min": req.duration_months_min,
                    "p_duration_max": req.duration_months_max,
                    "p_mileage_min": req.annual_mileage_min,
                    "p_mileage_max": req.annual_mileage_max,
                },
            )
        )

        rows = resp.data or []
        results: dict[str, VehiclePrices] = {}

        for row in rows:
            vid = str(row["vehicle_id"])
            found = bool(row["found"])
            variants_count = int(row.get("variants_count") or 0)

            if not found:
                results[vid] = VehiclePrices(
                    price_for_params=PriceForParamsResponse(
                        vehicle_id=vid, found=False, variants_count=variants_count
                    ),
                    variants=[],
                )
                continue

            # Map the best match returned by RPC
            best_match = PriceForParamsResponse(
                vehicle_id=vid,
                duration_months=row.get("duration_months"),
                annual_mileage=row.get("annual_mileage"),
                monthly_price_net=round(float(row.get("monthly_price_net") or 0), 2),
                calculated_at=row.get("calculated_at"),
                found=True,
                variants_count=variants_count,
                tire_class=row.get("tire_class"),
                service_type=row.get("service_type"),
                kalkulacja_id=row.get("kalkulacja_id"),
            )

            # For batch search, we primarily care about the main price.
            # Other variants (different calculations) can be fetched on-demand if needed,
            # but here we return the best one found as the primary result.
            results[vid] = VehiclePrices(
                price_for_params=best_match,
                variants=[],  # Simplified to avoid data overflow in batch
            )

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
            return PriceForParamsResponse(
                vehicle_id=vehicle_id, found=False, variants_count=0
            )

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
            return PriceForParamsResponse(
                vehicle_id=vehicle_id, found=False, variants_count=variants_count
            )

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
