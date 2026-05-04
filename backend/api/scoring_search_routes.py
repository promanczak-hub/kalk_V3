"""FastAPI routes for the reverse_search scoring engine."""

import hashlib
import json
import logging

from datetime import datetime
import time
from typing import Any, Optional

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


def _normalize_transmission(raw: str | None) -> str | None:
    """Collapse marketing transmission names ("7-biegowa automatyczna", "s-tronic
    quattro", "MANUALNA, NA TYLNE KOŁA RWD") to one of two clean values:
    "Automatyczna" or "Manualna". Returns None if input is empty/unrecognized.
    Used so the search filter chip shows just two options instead of dozens.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    # Order matters: "automat" before "manual" since some strings contain both
    if "automat" in s or "s-tronic" in s or "dsg" in s or "tiptronic" in s or "cvt" in s:
        return "Automatyczna"
    if "manual" in s:
        return "Manualna"
    return None


def _normalize_drive_type(raw: str | None) -> str | None:
    """Collapse drive_type variants ("4X4", "2X4", "Napęd przedni", "Quattro",
    "xDrive") to the AI mapper's canonical enum: FWD / RWD / AWD.
    Returns None for ambiguous values like "2X4" (could be FWD or RWD).
    """
    if not raw:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    # AWD synonyms
    if s in {"AWD", "4WD", "4X4", "4MATIC", "QUATTRO", "XDRIVE", "4MOTION", "ALL4"} \
       or "AWD" in s or "4X4" in s or "4WD" in s \
       or "WSZYSTKIE KOŁA" in s or "4MOTION" in s or "QUATTRO" in s:
        return "AWD"
    # FWD synonyms
    if s == "FWD" or "FWD" in s or "PRZEDNI" in s or "FRONT" in s:
        return "FWD"
    # RWD synonyms
    if s == "RWD" or "RWD" in s or "TYLN" in s or "REAR" in s:
        return "RWD"
    return None


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


def _parse_price_to_net(price_str: str | None, domain: str | None) -> float | None:
    """Helper to convert raw price string to a netto float.
    Default VAT is 23%. If domain is 'netto', returns as-is.
    If 'brutto' or unknown, divides by 1.23.
    """
    if not price_str:
        return None
    try:
        cleaned = (
            price_str.replace(" ", "")
            .replace("\xa0", "")
            .replace("PLN", "")
            .replace("zł", "")
        )
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        elif cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

        cleaned = "".join(c for c in cleaned if c.isdigit() or c == ".")

        val = float(cleaned)
        if domain == "netto":
            return round(val, 2)
        # Default to brutto -> netto conversion (1.23)
        return round(val / 1.23, 2)
    except (ValueError, TypeError):
        return None


def _build_similar_vehicle_match(row: dict[str, Any]) -> SimilarVehicleMatch:
    """Build a SimilarVehicleMatch from a raw RPC row dict.

    Handles both single and batch RPC variants (some field names differ),
    and maps the similarity_reasons JSONB payload to the SimilarityReasons model.
    """
    raw_reasons = row.get("similarity_reasons")
    similarity_reasons: SimilarityReasons | None = None
    price_domain = row.get("price_domain", "brutto")

    if isinstance(raw_reasons, dict):
        base_price_raw = raw_reasons.get("base_price")
        base_price_val = float(base_price_raw) if base_price_raw is not None else None

        # Convert base_price to net if needed
        if base_price_val is not None and price_domain == "brutto":
            base_price_val = round(base_price_val / 1.23, 2)

        def _opt_float(key: str) -> Optional[float]:
            v = raw_reasons.get(key)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        def _opt_int(key: str) -> Optional[int]:
            v = raw_reasons.get(key)
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        similarity_reasons = SimilarityReasons(
            samar_match=bool(raw_reasons.get("samar_match", False)),
            body_match=bool(raw_reasons.get("body_match", False)),
            fuel_match=bool(raw_reasons.get("fuel_match", False)),
            drive_match=bool(raw_reasons.get("drive_match", False)),
            equipment_match=bool(raw_reasons.get("equipment_match", False)),
            is_same_brand=bool(raw_reasons.get("is_same_brand", False)),
            equipment_similarity_pct=_opt_float("equipment_similarity_pct"),
            price_pct_diff=_opt_float("price_pct_diff"),
            is_cheaper=raw_reasons.get("is_cheaper"),
            samar_category=raw_reasons.get("samar_category"),
            body_style=raw_reasons.get("body_style"),
            base_price=base_price_val,
            paid_options=raw_reasons.get("paid_options"),
            is_fallback_match=bool(raw_reasons.get("is_fallback_match", False)),
            # V2 enrichment fields (gracefully None if RPC nie zwraca)
            discount_pct=_opt_float("discount_pct"),
            final_price_net=_opt_float("final_price_net"),
            final_price_pct_diff=_opt_float("final_price_pct_diff"),
            discount_pct_diff=_opt_float("discount_pct_diff"),
            payload_kg=_opt_int("payload_kg"),
            cargo_volume_m3=_opt_float("cargo_volume_m3"),
            body_type=raw_reasons.get("body_type"),
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
        price_domain=price_domain,
        similarity_reasons=similarity_reasons,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/scoring-search/available-filters")
def get_available_filters(request: AvailableFiltersRequest) -> dict[str, Any]:
    """Return dynamic facets (enums, ranges).

    The original `rpc_get_available_filters` was dropped on 2026-04-27 along with the
    rest of `reverse_search.*`. Until we rebuild facet aggregation in Python, return
    an empty shape so the frontend doesn't 500 — it will simply render no facets.
    """
    # Empty but well-typed shape - matches roughly what the old RPC returned, so
    # frontend code that destructures keys won't crash on undefined.
    return {
        "brands": [],
        "models": [],
        "body_types": [],
        "fuels": [],
        "transmissions": [],
        "drive_types": [],
        "samar_classes": [],
        "trim_levels": [],
        "ranges": {},
        "_notice": "facets temporarily unavailable - rpc_get_available_filters dropped 2026-04-27",
    }


@router.post("/scoring-search/search")
def run_scoring_search(request: ScoringSearchRequest) -> ScoringSearchResponse:
    """Vector-based vehicle search backed by rpc_search_vehicles_multi_vector.

    Was previously backed by the dropped public.rpc_reverse_search. Now:
      • If `semantic_query` is provided → embed it and call multi-vector RPC.
      • Otherwise → fall back to a plain SELECT with hard filters
        (brands / models / samar_class names) ranked by recency.
    Hard filters (samar_class_ids, brands, models) are always applied as a post-filter.
    """
    params_hash = _params_hash(request.model_dump_json())
    cache_key = f"{_PREFIX}search:{params_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: search [%s]", params_hash)
        matches = [ScoringSearchMatch(**row) for row in cached["results_raw"]]
        page_results = matches[request.offset : request.offset + request.limit]
        return ScoringSearchResponse(results=page_results, total_count=cached["total"])

    sb = supabase
    step = "init"
    try:
        # ── 1. Resolve hard-filter samar class names from samar_class_ids (post-filter) ──
        step = "resolve_samar_names"
        samar_class_names: set[str] | None = None
        if request.samar_class_ids:
            samar_resp = _supabase_execute_with_retry(
                sb.table("samar_classes")
                .select("name")
                .in_("id", request.samar_class_ids)
            )
            samar_class_names = {
                r["name"] for r in (samar_resp.data or []) if r.get("name")
            }

        brand_filter: set[str] | None = (
            {b.lower() for b in request.brands} if request.brands else None
        )
        model_filter: set[str] | None = (
            {m.lower() for m in request.models} if request.models else None
        )
        trim_filter: set[str] | None = (
            {t.lower() for t in request.trims} if request.trims else None
        )

        rows: list[dict] = []

        if request.semantic_query:
            # ── 2a. Vector path: embed query → multi-vector RPC ──
            step = "generate_embedding"
            logger.info(
                "Generating embedding for semantic query: '%s'", request.semantic_query
            )
            semantic_vector = generate_embedding(request.semantic_query)
            if semantic_vector is None:
                raise HTTPException(
                    status_code=502,
                    detail="Embedding service unavailable - cannot run semantic search",
                )

            step = "rpc_search_vehicles_multi_vector"
            # Wide candidate pool — post-filter narrows it. Hard cap so we don't blow up.
            candidate_limit = max(request.limit + request.offset, 100) * 3
            resp = _supabase_execute_with_retry(
                sb.rpc(
                    "rpc_search_vehicles_multi_vector",
                    {
                        "p_query_embedding": semantic_vector,
                        "p_weight_use_case": 0.4,
                        "p_weight_specs": 0.4,
                        "p_weight_equipment": 0.2,
                        "p_limit": candidate_limit,
                        "p_min_similarity": 30.0,
                        "p_required_feature_keys": None,
                    },
                )
            )
            rows = resp.data or []
        else:
            # ── 2b. No-query path: plain SELECT with hard filters, recency ranked ──
            step = "fallback_select_vehicle_synthesis"
            q = (
                sb.table("vehicle_synthesis")
                .select("id,brand,model,synthesis_data")
                .eq("verification_status", "completed")
                .order("created_at", desc=True)
                .limit(max(request.limit + request.offset, 100) * 3)
            )
            if request.vehicle_ids:
                q = q.in_("id", request.vehicle_ids)
            resp = _supabase_execute_with_retry(q)
            for r in resp.data or []:
                sd = r.get("synthesis_data") or {}
                cs = sd.get("card_summary") or {}
                mapped = sd.get("mapped_ai_data") or {}
                rows.append(
                    {
                        "vehicle_id": r["id"],
                        "brand": r.get("brand"),
                        "model": r.get("model"),
                        "version": cs.get("trim_level"),
                        "samar_category": mapped.get("samar_category"),
                        "fuel": mapped.get("fuel") or cs.get("fuel"),
                        "transmission": mapped.get("gearbox") or cs.get("transmission"),
                        "drive_type": mapped.get("drive_type") or cs.get("drivetrain") or cs.get("drive_type"),
                        "body_style": mapped.get("body_style") or cs.get("body_style"),
                        "power_hp": cs.get("power_hp"),
                        "base_price": _parse_numeric(cs.get("base_price")),
                        "score_total_pct": None,
                    }
                )

        # ── 3. Post-filter and map to ScoringSearchMatch ──
        # Normalize transmission and drive_type across both paths (vector RPC +
        # fallback SELECT) to canonical enum values, so filter chips collapse to
        # the small set defined by the AI mapper instead of dozens of variants.
        for row in rows:
            row["transmission"] = _normalize_transmission(row.get("transmission"))
            row["drive_type"] = _normalize_drive_type(row.get("drive_type"))

        step = "post_filter_and_map"
        all_matches: list[ScoringSearchMatch] = []
        for row in rows:
            brand = (row.get("brand") or "").lower()
            model = (row.get("model") or "").lower()
            version = (row.get("version") or "").lower()
            samar_cat = row.get("samar_category") or ""

            if brand_filter and brand and brand not in brand_filter:
                continue
            if model_filter and model and model not in model_filter:
                continue
            if trim_filter and version and version not in trim_filter:
                continue
            if samar_class_names is not None and samar_cat not in samar_class_names:
                continue

            base_price = row.get("base_price")
            score = row.get("score_total_pct")
            all_matches.append(
                ScoringSearchMatch(
                    vehicle_id=row.get("vehicle_id"),
                    brand=row.get("brand"),
                    model=row.get("model"),
                    version=row.get("version"),
                    match_score_pct=float(score) if score is not None else 100.0,
                    matched_features=[],
                    missing_features=[],
                    best_monthly_price=None,
                    fuel_type=row.get("fuel"),
                    power_hp=row.get("power_hp"),
                    transmission=row.get("transmission"),
                    drive_type=row.get("drive_type"),
                    body_style=row.get("body_style"),
                    base_price_net=float(base_price) if base_price else None,
                    price_domain="netto",
                    semantic_hit_reason=(
                        f"use_case {row.get('score_use_case_pct')}% / "
                        f"specs {row.get('score_specs_pct')}% / "
                        f"equipment {row.get('score_equipment_pct')}%"
                        if request.semantic_query and score is not None
                        else None
                    ),
                    trim_level=row.get("version"),
                    vehicle_class=row.get("samar_category"),
                )
            )

        _redis_set(
            cache_key,
            {
                "results_raw": [m.model_dump() for m in all_matches],
                "total": len(all_matches),
            },
            _TTL_SEARCH,
        )

        page_results = all_matches[request.offset : request.offset + request.limit]
        return ScoringSearchResponse(results=page_results, total_count=len(all_matches))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "POST /scoring-search/search failed at step=%s exc_type=%s",
            step,
            type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__} at step '{step}': {e}",
        )


def _parse_numeric(val: Any) -> float | None:
    """Best-effort parse of a price string into float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace(",", ".").strip()
        # Strip non-numeric except dot
        digits = "".join(c for c in cleaned if c.isdigit() or c == ".")
        try:
            return float(digits) if digits else None
        except ValueError:
            return None
    return None


@router.get("/scoring-search/initial-data", response_model=InitialDataResponse)
def get_initial_data() -> InitialDataResponse:
    """Aggregate brands / models / trims / samar classes / body types from vehicle_synthesis.

    Was previously backed by the dropped reverse_search.rpc_get_scoring_initial_data RPC.
    Now we aggregate directly in Python — keeps the same response shape so the frontend
    is unchanged.
    """
    cache_key = f"{_PREFIX}initial_data"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: initial-data")
        return InitialDataResponse(**cached)

    sb = supabase
    step = "init"
    try:
        # ── 1. Pull synthesis rows (brand, model, synthesis_data only — keep payload small) ──
        step = "fetch_vehicle_synthesis"
        rows_resp = _supabase_execute_with_retry(
            sb.table("vehicle_synthesis")
            .select("brand,model,synthesis_data")
            .eq("verification_status", "completed")
        )
        rows = rows_resp.data or []

        # ── 2. Pull samar classes (id, name) ──
        step = "fetch_samar_classes"
        samar_resp = _supabase_execute_with_retry(
            sb.table("samar_classes").select("id,name").order("id")
        )
        samar_classes = [
            {"id": r["id"], "name": r["name"]} for r in (samar_resp.data or [])
        ]

        # ── 3. Aggregate in-memory ──
        step = "aggregate"
        brand_set: set[str] = set()
        model_set: set[str] = set()
        brand_models: dict[str, set[str]] = {}
        brand_counts: dict[str, int] = {}
        trim_levels: dict[str, set[str]] = {}
        body_counts: dict[str, int] = {}

        for r in rows:
            brand = (r.get("brand") or "").strip()
            model = (r.get("model") or "").strip()
            if not brand or not model:
                continue

            brand_set.add(brand)
            model_set.add(model)
            brand_models.setdefault(brand, set()).add(model)
            brand_counts[brand] = brand_counts.get(brand, 0) + 1

            sd = r.get("synthesis_data") or {}
            cs = sd.get("card_summary") or {}
            mapped = sd.get("mapped_ai_data") or {}

            trim = (cs.get("trim_level") or "").strip()
            if trim:
                trim_levels.setdefault(f"{brand}|{model}", set()).add(trim)

            body_style = (
                mapped.get("body_style") or cs.get("body_style") or ""
            ).strip()
            if body_style:
                body_counts[body_style] = body_counts.get(body_style, 0) + 1

        result = InitialDataResponse(
            brands=sorted(brand_set),
            models=sorted(model_set),
            brand_model_map={b: sorted(ms) for b, ms in brand_models.items()},
            brand_counts=brand_counts,
            trim_level_map={k: sorted(v) for k, v in trim_levels.items()},
            samar_classes=samar_classes,
            body_types=[
                {"name": n, "count": c}
                for n, c in sorted(body_counts.items(), key=lambda x: -x[1])
            ],
        )

        _redis_set(cache_key, result.model_dump(), _TTL_INITIAL_DATA)
        return result
    except Exception as e:
        logger.exception(
            "GET /scoring-search/initial-data failed at step=%s exc_type=%s",
            step,
            type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__} at step '{step}': {e}",
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

    # Cache key generation
    cache_payload = f"{vehicle_id}:{limit}:{duration_months}:{annual_mileage}:{mode}"
    cache_key = f"{_PREFIX}similar:{_params_hash(cache_payload)}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: similar [%s]", vehicle_id)
        return [SimilarVehicleMatch(**row) for row in cached]

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

        results = [_build_similar_vehicle_match(row) for row in resp.data]
        _redis_set(cache_key, [r.model_dump() for r in results], 10800)
        return results
    except Exception as e:
        logger.exception("Error calling %s: %s", method, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch similar vehicles: {e}"
        )


class BlendAlternativesRequest(BaseModel):
    duration_months: int | None = None
    annual_mileage: int | None = None
    requirements: List[Any] = []


def _filter_semantic_candidates(
    sb, candidates, must_haves
) -> list[SimilarVehicleMatch]:
    if not must_haves:
        return [
            _build_similar_vehicle_match(row["similarity_json"]) for row in candidates
        ]

    candidate_ids = [
        row["similarity_json"]["vehicle_id"]
        for row in candidates
        if "similarity_json" in row
    ]
    if not candidate_ids:
        return []

    # 1. Fetch synthesis data for options check
    synthesis_resp = _supabase_execute_with_retry(
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .in_("id", candidate_ids)
    )
    synthesis_map = {
        row["id"]: row["synthesis_data"] for row in (synthesis_resp.data or [])
    }

    # 2. Fetch features directly using REST URL override to hit reverse_search schema
    features_resp = _supabase_execute_with_retry(
        sb.schema("reverse_search")
        .table("vehicle_features_summary_view")
        .select(
            "source_vehicle_id, feature_key, resolved_value_bool, resolved_value_text, resolved_value_num"
        )
        .in_("source_vehicle_id", candidate_ids)
    )

    features_map = {}
    for row in features_resp.data or []:
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

            if fkey in (
                "dummy",
                "duration_months",
                "annual_mileage",
                "margin_pct",
                "monthly_price_net",
            ):
                continue

            match = False
            if str(fkey).startswith("opt_std:"):
                opt_name = fkey[8:]
                std_opts = (
                    synthesis_map.get(vid, {})
                    .get("card_summary", {})
                    .get("standard_equipment", [])
                )
                if opt_name in std_opts:
                    match = True
            elif str(fkey).startswith("opt_paid:"):
                opt_name = fkey[9:]
                paid_opts = (
                    synthesis_map.get(vid, {})
                    .get("card_summary", {})
                    .get("paid_options", [])
                )
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
                            match = v_num >= num if op == "gte" else v_num <= num
                        except (ValueError, TypeError):
                            pass
                elif op == "in" and isinstance(val, list):
                    match = feat.get("resolved_value_text") in val

            if not match:
                ok = False
                break

        if ok:
            filtered_results.append(_build_similar_vehicle_match(sim_json))

    return filtered_results


@router.post(
    "/scoring-search/vehicle/{vehicle_id}/alternatives-blend",
    response_model=list[SimilarVehicleMatch],
)
def get_vehicle_alternatives_blend(
    vehicle_id: str, request: BlendAlternativesRequest
) -> list[SimilarVehicleMatch]:
    """Get a blend of 5 distinct alternative vehicles based on AI synthetic vectors."""
    sb = supabase
    try:
        synthetic_queries = {
            "cheaper": (
                "✨ AI: Oszczędniejszy wybór",
                "Budget friendly, affordable, economical, low cost of ownership, high value for money, cheap to maintain, basic standard.",
            ),
            "stronger": (
                "✨ AI: Większa dynamika",
                "High performance, powerful engine, fast acceleration, sporty driving, huge horsepower, high torque, dynamic.",
            ),
            "more_comfortable": (
                "✨ AI: Wyższy komfort",
                "Premium comfort, smooth suspension, quiet cabin, ergonomic seats, massage function, luxury interior materials, dual zone climate control, ample legroom.",
            ),
            "safer": (
                "✨ AI: Bezpieczeństwo",
                "Advanced safety systems, highest NCAP rating, multiple airbags, collision avoidance, blind spot monitoring, lane keep assist, robust structure.",
            ),
            "greener": (
                "✨ AI: Bardziej ekologiczny",
                "Eco-friendly, full electric, plug-in hybrid, low emissions, green energy, sustainable, low fuel consumption.",
            ),
        }

        limit_to_fetch = 10 if request.requirements else 2
        used_vehicle_ids = {vehicle_id}
        final_results = []

        must_haves = [
            req
            for req in request.requirements
            if isinstance(req, dict) and req.get("requirement") == "MUST_HAVE"
        ]

        for cat_key, (ai_label, query_text) in synthetic_queries.items():
            cache_key_embed = f"{_PREFIX}embed:{_params_hash(query_text)}"
            synthetic_vector = _redis_get(cache_key_embed)

            if synthetic_vector is None:
                logger.info("Generating embedding for synthetic query: '%s'", cat_key)
                synthetic_vector = generate_embedding(query_text)
                if synthetic_vector:
                    _redis_set(cache_key_embed, synthetic_vector, 2592000)

            if not synthetic_vector:
                continue

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
            filtered_matches = _filter_semantic_candidates(sb, candidates, must_haves)

            # Find the best match that hasn't been used yet
            found_match = None
            for match in filtered_matches:
                if match.vehicle_id not in used_vehicle_ids:
                    match.ai_label = ai_label
                    found_match = match
                    used_vehicle_ids.add(match.vehicle_id)
                    break

            if found_match:
                final_results.append(found_match)

        return final_results

    except Exception as e:
        logger.exception("Error calling rpc_get_alternatives_semantic blend: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch alternatives blend: {e}"
        )


@router.post(
    "/scoring-search/cache/batch-similar",
    response_model=SimilarBatchResponse,
)
def get_batch_similar_vehicles(req: SimilarBatchRequest) -> SimilarBatchResponse:
    """Return similar vehicles for multiple vehicle IDs in one DB query. Supports 'rule-based' and 'semantic'."""

    params_hash = _params_hash(req.model_dump_json())
    cache_key = f"{_PREFIX}batch_similar:{params_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: batch-similar [%s]", params_hash)

        # Odbudowa ze słownika
        restored_results: dict[str, list[SimilarVehicleMatch]] = {}
        for vid, cars in cached.get("results", {}).items():
            restored_results[vid] = [SimilarVehicleMatch(**c) for c in cars]

        return SimilarBatchResponse(results=restored_results)

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

        resp_obj = SimilarBatchResponse(results=results)

        # Serialize fully using model dumps for the cache
        serialized_results: dict[str, Any] = {}
        for k, v in results.items():
            serialized_results[k] = [m.model_dump() for m in v]

        _redis_set(cache_key, {"results": serialized_results}, _TTL_SEARCH)

        return resp_obj
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
            .eq("duration_months", duration_months)
            .eq("annual_mileage", annual_mileage)
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

        # Prefer the user-selected calculation when set and present in cache;
        # otherwise fall back to the most recently computed one.
        try:
            synth_resp = (
                sb.table("vehicle_synthesis")
                .select("selected_kalkulacja_id")
                .eq("id", vehicle_id)
                .limit(1)
                .execute()
            )
            synth_rows = synth_resp.data or []
            user_selected = (
                synth_rows[0].get("selected_kalkulacja_id") if synth_rows else None
            )
        except Exception:
            user_selected = None

        latest_kid = None
        if user_selected and user_selected in calc_map:
            latest_kid = user_selected
        elif kalk_times:
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
