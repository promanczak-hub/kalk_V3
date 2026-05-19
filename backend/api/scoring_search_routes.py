"""FastAPI routes for the reverse_search scoring engine.

Refactor 2026-05-19: extracted ~615 LOC of helpers to `scoring_search_helpers.py`.
The underscored names below are thin aliases kept for in-file callsite stability.
"""

import json
import logging
import re

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from celery.result import AsyncResult

from core.database import supabase, get_admin_client
from core.body_type_matcher import normalize_body_style_for_display
from core.celery_app import celery_app
from core.models_scoring_search import (
    AvailableFiltersRequest,
    BestFitVariant,
    ComparisonSnapshotRequest,
    ComparisonSnapshotResponse,
    ScoringSearchRequest,
    ScoringSearchResponse,
    ScoringSearchMatch,
    InitialDataResponse,
    SimilarVehicleMatch,
    SimilarityReasons,
    TrimsAndOptionsRequest,
    TrimsAndOptionsResponse,
    OptionItem,
    OptionLineItem,
    PackageContentsResponse,
    PackageSubFeature,
    PriceForParamsResponse,
    SimilarBatchRequest,
    SimilarBatchResponse,
    VehicleSnapshot,
    WrCurvePoint,
)
from typing import List, Dict
from core.redis_cache import (
    _get_client,
    _PREFIX,
    get_cache_stats,
)
from core.embeddings import generate_embedding

from api.scoring_search_helpers import (
    VAT_RATE,
    TTL_FILTERS as _TTL_FILTERS,
    TTL_INITIAL_DATA as _TTL_INITIAL_DATA,
    TTL_SEARCH as _TTL_SEARCH,
    BODY_TYPE_FIELDS as _BODY_TYPE_FIELDS,
    PRESENT_STATUSES as _PRESENT_STATUSES,
    attach_kalkulacja_snapshot_to_matches as _attach_kalkulacja_snapshot_to_matches,
    build_similar_vehicle_match as _build_similar_vehicle_match,
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    extract_option_line_items as _extract_option_line_items,
    fetch_kalkulacja_snapshot_params as _fetch_kalkulacja_snapshot_params,
    normalize_drive_type as _normalize_drive_type,
    normalize_transmission as _normalize_transmission,
    params_hash as _params_hash,
    parse_numeric as _parse_numeric,
    parse_price_numeric as _parse_price_numeric,
    parse_price_pair as _parse_price_pair,
    parse_price_to_net as _parse_price_to_net,
    percentile as _percentile,
    redis_get as _redis_get,
    redis_set as _redis_set,
    resolve_candidate_vehicle_ids as _resolve_candidate_vehicle_ids,
    resolve_price_domain as _resolve_price_domain,
    supabase_execute_with_retry as _supabase_execute_with_retry,
    vehicle_body_styles as _vehicle_body_styles,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring_search"])




@router.post("/scoring-search/available-filters")
def get_available_filters(request: AvailableFiltersRequest) -> dict[str, Any]:
    """Aggregate boolean + numeric range filters from `reverse_search.vehicle_specs_normalized`.

    Replaces the dropped `rpc_get_available_filters`. Returns counts/min/max scoped
    to the brand/model/body_type filter on the request. Numeric ranges are clipped
    at the 5th/95th percentile to keep sliders usable when source data has outliers.
    """
    payload_hash = _params_hash(request.model_dump_json())
    cache_key = f"{_PREFIX}available_filters:{payload_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        return cached

    sb = supabase
    empty_response: dict[str, Any] = {
        "filters_provided": True,
        "facet_groups": [],
        "range_filters": [],
        "boolean_filters": [],
    }

    try:
        vehicle_ids = _resolve_candidate_vehicle_ids(request)
        if not vehicle_ids:
            return empty_response

        # ── Feature catalog (small — 330 rows). Index by feature_id for fast lookup. ──
        feat_resp = _supabase_execute_with_retry(
            sb.schema("reverse_search")
            .table("universal_features")
            .select("id, feature_key, display_name, feature_type, category, category_id, sort_order")
            .eq("is_filterable", True)
            .eq("is_active", True)
        )
        cat_resp = _supabase_execute_with_retry(
            sb.schema("reverse_search")
            .table("universal_feature_categories")
            .select("id, display_name")
            .eq("is_active", True)
        )
        cat_name_by_id = {c["id"]: c.get("display_name") for c in (cat_resp.data or [])}
        feat_by_id: dict[str, dict[str, Any]] = {}
        for f in feat_resp.data or []:
            feat_by_id[f["id"]] = {
                "feature_key": f["feature_key"],
                "display_name": f.get("display_name") or f["feature_key"],
                "feature_type": f.get("feature_type") or f.get("data_type") or "boolean",
                "group_name": cat_name_by_id.get(f.get("category_id"))
                or f.get("category")
                or "Inne",
                "sort_order": f.get("sort_order") or 100,
            }

        # ── Resolved values for these vehicles (paginated to avoid PostgREST 1000-row cap) ──
        all_specs: list[dict[str, Any]] = []
        chunk_size = 200  # vehicle ids per IN clause; PostgREST default cap is 1000 rows total
        for i in range(0, len(vehicle_ids), chunk_size):
            chunk = vehicle_ids[i : i + chunk_size]
            page = 0
            while True:
                resp = _supabase_execute_with_retry(
                    sb.schema("reverse_search")
                    .table("vehicle_specs_normalized")
                    .select("vehicle_id, feature_id, value_bool, value_numeric, resolved_status")
                    .in_("vehicle_id", chunk)
                    .in_("resolved_status", list(_PRESENT_STATUSES))
                    .range(page * 1000, page * 1000 + 999)
                )
                rows = resp.data or []
                all_specs.extend(rows)
                if len(rows) < 1000:
                    break
                page += 1

        # ── Aggregate booleans: count distinct vehicles per feature where value_bool=true ──
        bool_vehicle_sets: dict[str, set[str]] = {}
        numeric_values: dict[str, list[float]] = {}
        for row in all_specs:
            feat = feat_by_id.get(row.get("feature_id"))
            if not feat:
                continue
            ftype = feat["feature_type"]
            vid = str(row.get("vehicle_id"))
            if ftype == "boolean":
                if row.get("value_bool") is True:
                    bool_vehicle_sets.setdefault(feat["feature_key"], set()).add(vid)
            elif ftype == "numeric":
                v = row.get("value_numeric")
                if v is None:
                    continue
                try:
                    numeric_values.setdefault(feat["feature_key"], []).append(float(v))
                except (TypeError, ValueError):
                    continue

        boolean_filters: list[dict[str, Any]] = []
        for feat in feat_by_id.values():
            if feat["feature_type"] != "boolean":
                continue
            cnt = len(bool_vehicle_sets.get(feat["feature_key"], ()))
            if cnt == 0:
                continue
            boolean_filters.append(
                {
                    "feature_key": feat["feature_key"],
                    "feature_name": feat["display_name"],
                    "group_name": feat["group_name"],
                    "parent_feature_key": None,
                    "facet_level": 0,
                    "is_primary_facet": False,
                    "cnt": cnt,
                }
            )
        boolean_filters.sort(key=lambda x: (-x["cnt"], x["feature_name"]))

        range_filters: list[dict[str, Any]] = []
        for feat in feat_by_id.values():
            if feat["feature_type"] != "numeric":
                continue
            vals = numeric_values.get(feat["feature_key"]) or []
            if len(vals) < 2:
                continue
            # Clip outliers (data has spurious entries like 19843 cm³). Round so
            # the slider snaps to clean integers.
            lo = round(_percentile(vals, 0.05))
            hi = round(_percentile(vals, 0.95))
            if hi <= lo:
                continue
            range_filters.append(
                {
                    "feature_key": feat["feature_key"],
                    "feature_name": feat["display_name"],
                    "group_name": feat["group_name"],
                    "parent_feature_key": None,
                    "facet_level": 0,
                    "is_primary_facet": False,
                    "min_val": lo,
                    "max_val": hi,
                }
            )
        range_filters.sort(key=lambda x: (x["group_name"], x["feature_name"]))

        response: dict[str, Any] = {
            "filters_provided": True,
            "facet_groups": [],
            "range_filters": range_filters,
            "boolean_filters": boolean_filters,
        }
        _redis_set(cache_key, response, _TTL_FILTERS)
        return response
    except Exception as exc:
        logger.exception("get_available_filters failed: %s", exc)
        return empty_response


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

        # ── Extract spec filters (drive_type, transmission, fuel, body_style)
        # from requirements[] sent by the frontend chips. These were previously
        # ignored — search returned all vehicles regardless of which chips were
        # selected. Normalize values so filter chips ("RWD", "Manualna") match
        # the normalized row values produced by _normalize_* helpers below.
        def _extract_req_values(feature_key: str) -> set[str] | None:
            vals: set[str] = set()
            for req in request.requirements or []:
                if not isinstance(req, BaseModel):
                    req_dict = req if isinstance(req, dict) else {}
                else:
                    req_dict = req.model_dump()
                if req_dict.get("feature_key") != feature_key:
                    continue
                v = req_dict.get("value")
                if isinstance(v, list):
                    vals.update(str(x) for x in v if x is not None)
                elif isinstance(v, str):
                    vals.add(v)
            return vals or None

        drive_type_filter_raw = _extract_req_values("drive_type")
        drive_type_filter: set[str] | None = (
            {_normalize_drive_type(v) for v in drive_type_filter_raw}
            if drive_type_filter_raw else None
        )
        transmission_filter_raw = _extract_req_values("transmission")
        transmission_filter: set[str] | None = (
            {_normalize_transmission(v) for v in transmission_filter_raw}
            if transmission_filter_raw else None
        )
        fuel_filter_raw = _extract_req_values("fuel")
        fuel_filter: set[str] | None = (
            {v.lower() for v in fuel_filter_raw} if fuel_filter_raw else None
        )
        body_style_filter_raw = _extract_req_values("body_style")
        body_style_filter: set[str] | None = (
            {v.lower() for v in body_style_filter_raw} if body_style_filter_raw else None
        )

        # Equipment chip filters from the "Cechy dedykowane" tab. Frontend
        # toggles store feature_key="opt_std:<name>" (or "opt_paid:<name>")
        # with value="true". We strip the prefix and match name lowercased
        # against card_summary.standard_equipment / paid_options[].name.
        # Only MUST_HAVE constrains the result set; NICE_TO_HAVE is currently
        # ignored (no scoring for these yet).
        _SPECIAL_REQ_KEYS = {"drive_type", "transmission", "fuel", "body_style"}

        def _extract_req_values_with_prefix(prefix: str) -> set[str] | None:
            vals: set[str] = set()
            for req in request.requirements or []:
                if isinstance(req, BaseModel):
                    req_dict = req.model_dump()
                elif isinstance(req, dict):
                    req_dict = req
                else:
                    continue
                fk = req_dict.get("feature_key") or ""
                if not fk.startswith(prefix):
                    continue
                if req_dict.get("requirement") != "MUST_HAVE":
                    continue
                if str(req_dict.get("value")).lower() != "true":
                    continue
                name = fk[len(prefix):].strip().lower()
                if name:
                    vals.add(name)
            return vals or None

        opt_std_filter: set[str] | None = _extract_req_values_with_prefix("opt_std:")
        opt_paid_filter: set[str] | None = _extract_req_values_with_prefix("opt_paid:")

        # Universal boolean feature filters from the "Cechy uniwersalne" tab.
        # Anything in requirements[] that isn't one of the 4 special keys nor
        # an opt_*: prefixed equipment toggle is treated as a universal
        # feature_key referring to reverse_search.universal_features. MUST_HAVE
        # boolean values constrain the result; NICE_TO_HAVE / numeric ranges
        # are not yet wired here.
        universal_bool_keys: set[str] = set()
        for req in request.requirements or []:
            if isinstance(req, BaseModel):
                req_dict = req.model_dump()
            elif isinstance(req, dict):
                req_dict = req
            else:
                continue
            fk = req_dict.get("feature_key") or ""
            if not fk or fk in _SPECIAL_REQ_KEYS:
                continue
            if fk.startswith("opt_std:") or fk.startswith("opt_paid:"):
                continue
            if req_dict.get("requirement") != "MUST_HAVE":
                continue
            if str(req_dict.get("value")).lower() != "true":
                continue
            universal_bool_keys.add(fk)

        rows: list[dict] = []

        def _fetch_rows_plain_select() -> list[dict]:
            """Plain SELECT from vehicle_synthesis (no semantic ranking).
            Used both when no semantic_query is given AND as a safety fallback
            when multi-vector RPC returns 0 rows (e.g. embeddings not backfilled
            for completed vehicles)."""
            q = (
                sb.table("vehicle_synthesis")
                .select("id,brand,model,synthesis_data")
                .eq("verification_status", "completed")
                .order("created_at", desc=True)
                .limit(max(request.limit + request.offset, 100) * 3)
            )
            if request.vehicle_ids:
                q = q.in_("id", request.vehicle_ids)
            resp_local = _supabase_execute_with_retry(q)
            out: list[dict] = []
            for r in resp_local.data or []:
                sd = r.get("synthesis_data") or {}
                cs = sd.get("card_summary") or {}
                mapped = sd.get("mapped_ai_data") or {}
                out.append(
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
            return out

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
            if not rows:
                # Vector search returned nothing — most likely target vehicles
                # don't have multi-vector embeddings populated yet. Fall back to
                # plain SELECT so hard filters (body_style, brand, model) still
                # surface matches. Semantic ranking is lost; that's acceptable
                # while the embedding backfill catches up.
                logger.warning(
                    "rpc_search_vehicles_multi_vector returned 0 rows for query=%r; "
                    "falling back to plain SELECT (semantic ranking degraded)",
                    request.semantic_query,
                )
                step = "fallback_after_empty_vector"
                rows = _fetch_rows_plain_select()
        else:
            # ── 2b. No-query path: plain SELECT with hard filters, recency ranked ──
            step = "fallback_select_vehicle_synthesis"
            q = (
                sb.table("vehicle_synthesis")
                .select("id,brand,model,offer_number,created_at,synthesis_data")
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
                meta = sd.get("metadata") or {}
                domain = cs.get("price_domain")

                svc_eq = cs.get("service_equipment") or {}
                svc_eq_net = _parse_price_to_net(svc_eq.get("total_price_net"), "netto")
                factory_sum = 0.0
                service_sum = 0.0
                for opt in cs.get("paid_options") or []:
                    cat = (opt.get("category") or "").lower()
                    # See _extract_option_line_items — skip the "Zabudowa /
                    # Wyposażenie serwisowe" summary when service_equipment
                    # will contribute the same package below.
                    if "zabudowa" in cat and svc_eq_net:
                        continue
                    val = _parse_price_to_net(
                        opt.get("price"), opt.get("price_type") or domain
                    )
                    if val is None:
                        continue
                    if "fabryczn" in cat:
                        factory_sum += val
                    elif "serwis" in cat or "akcesori" in cat or "zabudowa" in cat:
                        service_sum += val
                if svc_eq_net:
                    service_sum += svc_eq_net

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
                        "body_style": normalize_body_style_for_display(
                            mapped.get("body_style") or cs.get("body_style")
                        ),
                        "power_hp": cs.get("power_hp"),
                        "base_price": _parse_price_to_net(cs.get("base_price"), domain),
                        "total_price_net": _parse_price_to_net(cs.get("total_price"), domain),
                        "factory_options_price_net": round(factory_sum, 2) if factory_sum else None,
                        "service_options_price_net": round(service_sum, 2) if service_sum else None,
                        "options_price_net": _parse_price_to_net(cs.get("options_price"), domain),
                        "engine_capacity": cs.get("engine_capacity"),
                        "engine_designation": cs.get("engine_designation"),
                        "configuration_code": meta.get("configuration_code") or sd.get("configuration_code"),
                        "offer_number": r.get("offer_number") or meta.get("offer_number") or sd.get("offer_number"),
                        "extraction_date": r.get("created_at"),
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

        # ── 3a. Prefetch equipment / universal feature data for filter chips ──
        # Vector-path rows don't carry synthesis_data, plain-SELECT rows already
        # consumed it but didn't materialize equipment lists into the row dict.
        # We do one batch round-trip when an equipment or universal-bool filter
        # is active, indexed by vehicle_id.
        vehicle_std_eq: dict[str, set[str]] = {}
        vehicle_paid_eq: dict[str, set[str]] = {}
        if opt_std_filter or opt_paid_filter:
            vid_list = [str(r.get("vehicle_id")) for r in rows if r.get("vehicle_id")]
            if vid_list:
                step = "prefetch_equipment_for_filters"
                eq_resp = _supabase_execute_with_retry(
                    sb.table("vehicle_synthesis")
                    .select("id, synthesis_data")
                    .in_("id", vid_list)
                )
                for r in eq_resp.data or []:
                    sd = r.get("synthesis_data") or {}
                    cs = sd.get("card_summary") or {}
                    vid = str(r.get("id"))
                    std_set = {
                        str(e).strip().lower()
                        for e in (cs.get("standard_equipment") or [])
                        if isinstance(e, str) and e.strip()
                    }
                    paid_set = {
                        str(po.get("name", "")).strip().lower()
                        for po in (cs.get("paid_options") or [])
                        if isinstance(po, dict) and po.get("name")
                    }
                    vehicle_std_eq[vid] = std_set
                    vehicle_paid_eq[vid] = paid_set

                # Also include package sub-features so a filter like
                # `opt_paid:system 360"` matches vehicles where the sub-feature is
                # nested inside a package (e.g. "Pakiet IMMERSIVE"). Source:
                # reverse_search.vehicle_feature_evidence rows written by the LLM
                # decomposer, joined to universal_features.display_name.
                if opt_paid_filter:
                    sub_resp = _supabase_execute_with_retry(
                        sb.schema("reverse_search")
                        .table("vehicle_feature_evidence")
                        .select("source_vehicle_id, universal_features(display_name)")
                        .eq("source_type", "package_decomposition")
                        .in_("source_vehicle_id", vid_list)
                    )
                    for s in sub_resp.data or []:
                        vid = str(s.get("source_vehicle_id") or "")
                        if not vid:
                            continue
                        uf = s.get("universal_features") or {}
                        name = (uf.get("display_name") or "").strip().lower()
                        if not name:
                            continue
                        vehicle_paid_eq.setdefault(vid, set()).add(name)

        vehicle_universal_bools: dict[str, set[str]] = {}
        if universal_bool_keys:
            vid_list = [str(r.get("vehicle_id")) for r in rows if r.get("vehicle_id")]
            if vid_list:
                step = "prefetch_universal_bools_for_filters"
                feat_resp = _supabase_execute_with_retry(
                    sb.schema("reverse_search")
                    .table("universal_features")
                    .select("id, feature_key")
                    .in_("feature_key", list(universal_bool_keys))
                )
                feat_id_to_key = {
                    f["id"]: f["feature_key"] for f in (feat_resp.data or [])
                }
                if feat_id_to_key:
                    spec_resp = _supabase_execute_with_retry(
                        sb.schema("reverse_search")
                        .table("vehicle_specs_normalized")
                        .select("vehicle_id, feature_id, value_bool, resolved_status")
                        .in_("vehicle_id", vid_list)
                        .in_("feature_id", list(feat_id_to_key.keys()))
                        .in_("resolved_status", list(_PRESENT_STATUSES))
                    )
                    for s in spec_resp.data or []:
                        if s.get("value_bool") is not True:
                            continue
                        fk = feat_id_to_key.get(s.get("feature_id"))
                        if not fk:
                            continue
                        vehicle_universal_bools.setdefault(
                            str(s.get("vehicle_id")), set()
                        ).add(fk)

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
            # Spec filters (chips selected in the sidebar) — compare against
            # normalized values so user-selected "RWD" matches normalized rows.
            if drive_type_filter is not None and row.get("drive_type") not in drive_type_filter:
                continue
            if transmission_filter is not None and row.get("transmission") not in transmission_filter:
                continue
            if fuel_filter is not None:
                row_fuel = (row.get("fuel") or "").lower()
                if row_fuel not in fuel_filter:
                    continue
            if body_style_filter is not None:
                row_body = (row.get("body_style") or "").lower()
                if row_body not in body_style_filter:
                    continue

            # Equipment chip filters — OR within each facet (vehicle keeps if it
            # has ANY of the selected names), AND across facets (std AND paid).
            # Standard e-commerce multi-select semantics: ticking 3 boxes asks
            # "any of these", not "all of these". Cross-facet AND keeps the
            # filter useful when combining categories.
            vid_str = str(row.get("vehicle_id") or "")
            if opt_std_filter is not None:
                if not (opt_std_filter & vehicle_std_eq.get(vid_str, set())):
                    continue
            if opt_paid_filter is not None:
                if not (opt_paid_filter & vehicle_paid_eq.get(vid_str, set())):
                    continue
            # Universal boolean feature_keys — vehicle must have ALL keys
            # resolved to value_bool=true with a "present" status.
            if universal_bool_keys:
                if not universal_bool_keys.issubset(
                    vehicle_universal_bools.get(vid_str, set())
                ):
                    continue

            base_price = row.get("base_price")
            score = row.get("score_total_pct")

            # Build matched_features list — every selected requirement that the
            # vehicle actually satisfies. With OR-within-facet semantics, a
            # surviving vehicle may have only a subset of the ticked options
            # (universal still AND, std/paid OR), so we explicitly list only
            # the intersections to give the UI accurate per-feature badges.
            matched_features_list: list[str] = []
            if universal_bool_keys:
                veh_bools = vehicle_universal_bools.get(vid_str, set())
                matched_features_list.extend(sorted(universal_bool_keys & veh_bools))
            if opt_std_filter:
                veh_std = vehicle_std_eq.get(vid_str, set())
                matched_features_list.extend(
                    f"opt_std:{n}" for n in sorted(opt_std_filter) if n in veh_std
                )
            if opt_paid_filter:
                veh_paid = vehicle_paid_eq.get(vid_str, set())
                matched_features_list.extend(
                    f"opt_paid:{n}" for n in sorted(opt_paid_filter) if n in veh_paid
                )

            all_matches.append(
                ScoringSearchMatch(
                    vehicle_id=row.get("vehicle_id"),
                    brand=row.get("brand"),
                    model=row.get("model"),
                    version=row.get("version"),
                    match_score_pct=float(score) if score is not None else 100.0,
                    matched_features=matched_features_list,
                    missing_features=[],
                    best_monthly_price=None,
                    fuel_type=row.get("fuel"),
                    power_hp=row.get("power_hp"),
                    transmission=row.get("transmission"),
                    drive_type=row.get("drive_type"),
                    body_style=row.get("body_style"),
                    base_price_net=float(base_price) if base_price else None,
                    total_price_net=row.get("total_price_net"),
                    options_price_net=row.get("options_price_net"),
                    factory_options_price_net=row.get("factory_options_price_net"),
                    service_options_price_net=row.get("service_options_price_net"),
                    engine_capacity=row.get("engine_capacity"),
                    engine_designation=row.get("engine_designation"),
                    configuration_code=row.get("configuration_code"),
                    offer_number=row.get("offer_number"),
                    extraction_date=row.get("extraction_date"),
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

        # ── 4. Attach pinned kalkulacje + factory/service option line items ──
        # Single roundtrip pulls both (a) selected_kalkulacja_ids for the
        # multi-card render and (b) the synthesis_data blob we parse for
        # paid_options breakdown shown by inline expand in the result card.
        # We also recompute every catalog total (net + gross) here from the
        # line items so the displayed sub-totals always add up to the displayed
        # catalog total — eliminating drift from earlier extractor stages.
        step = "attach_selected_kalkulacja_ids"
        vehicle_ids_in_results = [m.vehicle_id for m in all_matches if m.vehicle_id]
        if vehicle_ids_in_results:
            try:
                synth_resp = _supabase_execute_with_retry(
                    sb.table("vehicle_synthesis")
                    .select("id, selected_kalkulacja_ids, synthesis_data")
                    .in_("id", vehicle_ids_in_results)
                )
                pinned_map: dict[str, list[str]] = {}
                synth_map: dict[str, dict[str, Any]] = {}
                for r in synth_resp.data or []:
                    rid = str(r["id"])
                    pinned_map[rid] = list(r.get("selected_kalkulacja_ids") or [])
                    synth_map[rid] = r.get("synthesis_data") or {}
                for m in all_matches:
                    key = str(m.vehicle_id)
                    m.selected_kalkulacja_ids = pinned_map.get(key, [])
                    sd = synth_map.get(key, {})
                    cs = sd.get("card_summary") or {}
                    factory, service = _extract_option_line_items(cs)
                    m.factory_options = factory
                    m.service_options = service

                    base_net, base_gross = _parse_price_pair(
                        cs.get("base_price"), cs.get("price_domain")
                    )
                    factory_net = round(
                        sum(o.price_net for o in factory if o.price_net is not None), 2
                    ) if factory else None
                    factory_gross = round(
                        sum(o.price_gross for o in factory if o.price_gross is not None), 2
                    ) if factory else None
                    service_net = round(
                        sum(o.price_net for o in service if o.price_net is not None), 2
                    ) if service else None
                    service_gross = round(
                        sum(o.price_gross for o in service if o.price_gross is not None), 2
                    ) if service else None

                    if base_net is not None:
                        m.base_price_net = base_net
                    m.base_price_gross = base_gross
                    m.factory_options_price_net = factory_net
                    m.factory_options_price_gross = factory_gross
                    m.service_options_price_net = service_net
                    m.service_options_price_gross = service_gross
                    options_net_sum = (factory_net or 0) + (service_net or 0)
                    options_gross_sum = (factory_gross or 0) + (service_gross or 0)
                    m.options_price_net = round(options_net_sum, 2) or None
                    m.options_price_gross = round(options_gross_sum, 2) or None
                    m.total_price_net = round(
                        (base_net or 0) + options_net_sum, 2
                    ) or None
                    m.total_price_gross = round(
                        (base_gross or 0) + options_gross_sum, 2
                    ) or None
                    m.price_domain = "netto"
            except Exception:
                logger.exception("Failed to attach selected_kalkulacja_ids to search results")

        # ── 5. Auto-fit best variant per vehicle (server-side sweep) ──
        # When the user gave a budget but didn't pin duration/mileage/margin,
        # the result card otherwise shows a snapshot driven by UI defaults
        # (48mc / 80k km / margin 10%) — which has nothing to do with the
        # budget. Here we sweep `vehicle_matrix_cache` for each candidate,
        # pick the cheapest variant of the latest kalkulacja, and compute the
        # max margin that still fits the budget (clamped to auto_margin_cap_pct).
        if (
            request.fit_to_budget
            and request.monthly_budget
            and request.monthly_budget > 0
            and vehicle_ids_in_results
        ):
            step = "fit_to_budget_sweep"
            try:
                budget = float(request.monthly_budget)
                cap = max(0.0, min(float(request.auto_margin_cap_pct), 99.0))
                # Paginate past Supabase's 1000-row default. With ~212 cells
                # per vehicle, ~5 vehicles in search results overflows the
                # default page and newest cells silently get dropped.
                _PAGE = 1000
                sweep_rows: list[dict] = []
                _offset = 0
                while True:
                    _batch = _supabase_execute_with_retry(
                        sb.table("vehicle_matrix_cache")
                        .select(
                            "vehicle_id,duration_months,annual_mileage,monthly_price_net,"
                            "kalkulacja_id,tire_class,service_type,calculated_at"
                        )
                        .in_("vehicle_id", vehicle_ids_in_results)
                        .range(_offset, _offset + _PAGE - 1)
                    )
                    _rows = _batch.data or []
                    sweep_rows.extend(_rows)
                    if len(_rows) < _PAGE:
                        break
                    _offset += _PAGE
                rows_by_vehicle: dict[str, list[dict]] = {}
                all_kalk_ids: set[str] = set()
                for r in sweep_rows:
                    vid = str(r.get("vehicle_id") or "")
                    if not vid:
                        continue
                    rows_by_vehicle.setdefault(vid, []).append(r)
                    kid = r.get("kalkulacja_id")
                    if kid:
                        all_kalk_ids.add(str(kid))

                snapshot_by_kid = _fetch_kalkulacja_snapshot_params(list(all_kalk_ids))

                for m in all_matches:
                    rows = rows_by_vehicle.get(str(m.vehicle_id))
                    if not rows:
                        continue
                    # Latest kalkulacja for this vehicle (max calculated_at).
                    kalk_times: dict[str, datetime] = {}
                    for r in rows:
                        kid = r.get("kalkulacja_id") or ""
                        ca = r.get("calculated_at")
                        if not ca:
                            continue
                        try:
                            dt = datetime.fromisoformat(str(ca).replace("Z", "+00:00"))
                        except Exception:
                            continue
                        if kid not in kalk_times or dt > kalk_times[kid]:
                            kalk_times[kid] = dt
                    latest_kid = (
                        max(kalk_times, key=kalk_times.get) if kalk_times else None
                    )
                    latest_rows = (
                        [r for r in rows if (r.get("kalkulacja_id") or "") == (latest_kid or "")]
                        if latest_kid is not None
                        else rows
                    )
                    if not latest_rows:
                        latest_rows = rows
                    valid = [
                        r for r in latest_rows if r.get("monthly_price_net") is not None
                    ]
                    if not valid:
                        continue
                    best = min(valid, key=lambda r: float(r["monthly_price_net"]))
                    base = float(best["monthly_price_net"])

                    if base >= budget:
                        applied = 0.0
                        final = base
                        fits = False
                        over: Optional[float] = round(base - budget, 2)
                    else:
                        max_m = (1.0 - base / budget) * 100.0
                        applied = round(min(max_m, cap), 2)
                        final = round(base / (1.0 - applied / 100.0), 2)
                        fits = final <= budget + 0.01
                        over = None if fits else round(final - budget, 2)

                    best_kid = best.get("kalkulacja_id")
                    snap = snapshot_by_kid.get(str(best_kid)) if best_kid else None
                    m.best_fit_variant = BestFitVariant(
                        duration_months=int(best["duration_months"]),
                        annual_mileage=int(best["annual_mileage"]),
                        base_price_net=round(base, 2),
                        applied_margin_pct=applied,
                        monthly_price_net=round(final, 2),
                        fits_budget=fits,
                        over_budget_pln=over,
                        kalkulacja_id=best_kid,
                        tire_class=best.get("tire_class"),
                        service_type=best.get("service_type"),
                        variants_count=len(latest_rows),
                        **(snap or {}),
                    )
                    # Surface the auto-fit price + margin via the existing fields
                    # too, so older UI paths that don't yet read best_fit_variant
                    # still display sensible numbers.
                    m.best_monthly_price = round(final, 2)
                    m.applied_margin_pct = applied
            except Exception:
                logger.exception("fit_to_budget sweep failed; leaving best_fit_variant=None")

        # ── 6. Default snapshot for the comparison-chart view ──
        # Attach the cost decomposition (WR%, koszty techniczne, TCO/mc) for the
        # default (36mc, 30000 km) pair, sourced from vehicle_matrix_cache. Lets
        # the chart view render immediately without an extra round-trip.
        if vehicle_ids_in_results:
            step = "attach_default_snapshot"
            try:
                snap_rows = _fetch_snapshot_rows(vehicle_ids_in_results, 30000)
                rows_by_vehicle_snap: dict[str, list[dict[str, Any]]] = {}
                for r in snap_rows:
                    rows_by_vehicle_snap.setdefault(str(r.get("vehicle_id")), []).append(r)
                for m in all_matches:
                    vid = str(m.vehicle_id)
                    m.default_snapshot = _build_snapshot_for_vehicle(
                        rows_by_vehicle_snap.get(vid, []),
                        vehicle_id=vid,
                        target_months=36,
                        include_curve=False,
                    )
            except Exception:
                logger.exception("attach_default_snapshot failed; leaving default_snapshot=None")

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

            body_style = mapped.get("body_style") or cs.get("body_style")
            key = normalize_body_style_for_display(body_style)
            if key:
                body_counts[key] = body_counts.get(key, 0) + 1

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
        samar_class_names: list[str] | None = None
        if request.samar_class_ids:
            samar_resp = _supabase_execute_with_retry(
                sb.table("samar_classes")
                .select("name")
                .in_("id", request.samar_class_ids)
            )
            samar_class_names = [
                r["name"] for r in (samar_resp.data or []) if r.get("name")
            ] or None

        resp = sb.rpc(
            "rpc_get_trims_and_options",
            {
                "p_brands": request.brands,
                "p_models": request.models,
                "p_body_types": request.body_types,
                "p_samar_class_names": samar_class_names,
                "p_transmissions": request.transmissions,
                "p_drive_types": request.drive_types,
                "p_fuel_types": request.fuel_types,
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


def _enqueue_embedding_with_dedupe(vehicle_id: str) -> bool:
    """Best-effort trigger generate_embedding_for_vehicle z 60s Redis dedupe.

    Zwraca True jeśli task został zaplanowany, False jeśli dedupe odsiał
    (już zaplanowany w ostatnich 60s) lub Redis/Celery padł. Nie rzuca.
    """
    dedupe_key = f"{_PREFIX}similar-trigger:{vehicle_id}"
    client = _get_client()
    if client is not None:
        try:
            # SETNX z TTL — atomic, zwraca True tylko jeśli klucz nie istniał
            if not client.set(dedupe_key, "1", ex=60, nx=True):
                logger.debug("Embedding trigger deduped for %s", vehicle_id)
                return False
        except Exception as exc:
            logger.debug("Redis dedupe failed for %s: %s — enqueuing anyway", vehicle_id, exc)
    # Wyślij task (z 2s countdown żeby ten request HTTP zdążył wrócić zanim
    # worker zacznie hammerować DB).
    try:
        celery_app.send_task(
            "tasks.enrichment_tasks.generate_embedding_for_vehicle",
            args=[vehicle_id],
            countdown=2,
        )
        logger.info("On-demand embedding triggered for %s", vehicle_id)
        return True
    except Exception as exc:
        logger.warning("Failed to enqueue embedding task for %s: %s", vehicle_id, exc)
        return False


@router.get(
    "/scoring-search/vehicle/{vehicle_id}/similar",
    response_model=list[SimilarVehicleMatch],
)
def get_similar_vehicles(
    vehicle_id: str,
    response: Response,
    limit: int = 5,
    duration_months: int | None = None,
    annual_mileage: int | None = None,
    mode: str = "rule-based",
) -> list[SimilarVehicleMatch]:
    """Get similar vehicles sorted by best monthly price net. Supports 'rule-based' (default) and 'semantic' modes.

    Ustawia response header `X-Similar-Status`:
    - `ready`  — źródłowy pojazd ma embeddingi i znaleziono dopasowania (lub RPC zwrócił rows)
    - `pending` — źródłowy pojazd nie ma embeddingów; zaplanowano on-demand generację
    - `empty`  — źródłowy pojazd ma embeddingi, ale RPC zwrócił 0 dopasowań
    Header jest backward-compat: stary frontend ignoruje, nowy go czyta i rozróżnia stany.
    """

    # Cache key generation
    cache_payload = f"{vehicle_id}:{limit}:{duration_months}:{annual_mileage}:{mode}"
    cache_key = f"{_PREFIX}similar:{_params_hash(cache_payload)}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: similar [%s]", vehicle_id)
        response.headers["X-Similar-Status"] = "ready" if cached else "empty"
        return [SimilarVehicleMatch(**row) for row in cached]

    # Service-role client: anon's 3s statement_timeout cancels semantic RPCs on cold cache
    sb = get_admin_client()

    # Pre-check: czy źródłowy pojazd ma embeddingi? Jeśli NULL — od razu
    # zwracamy [] z header `pending` i triggerujemy on-demand generację
    # (60s dedupe, żeby F5-spam nie hammerował Vertex AI).
    try:
        pre_resp = (
            sb.table("vehicle_synthesis")
            .select("semantic_embedding, vector_use_case, vector_specs, vector_equipment")
            .eq("id", vehicle_id)
            .limit(1)
            .execute()
        )
        if pre_resp.data:
            row = pre_resp.data[0]
            missing_any = any(
                row.get(col) is None
                for col in ("semantic_embedding", "vector_use_case", "vector_specs", "vector_equipment")
            )
            if missing_any:
                _enqueue_embedding_with_dedupe(vehicle_id)
                response.headers["X-Similar-Status"] = "pending"
                return []
    except Exception as exc:
        # Pre-check nie może wywrócić requestu — fallthrough do RPC.
        logger.debug("Pre-check embedding state failed for %s: %s", vehicle_id, exc)

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
            response.headers["X-Similar-Status"] = "empty"
            return []

        results = [_build_similar_vehicle_match(row) for row in resp.data]
        # Stamp each match with the kalkulacja-level snapshot so its card can
        # render the same params row (rabat / opony / ubezpieczenie / WIBOR /
        # marża bankowa) as the source vehicle's card.
        _attach_kalkulacja_snapshot_to_matches(results)
        _redis_set(cache_key, [r.model_dump() for r in results], 10800)
        response.headers["X-Similar-Status"] = "ready"
        return results
    except Exception as e:
        logger.exception("Error calling %s: %s", method, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch similar vehicles: {e}"
        )


@router.post(
    "/scoring-search/cache/batch-similar",
    response_model=SimilarBatchResponse,
)
def get_batch_similar_vehicles(req: SimilarBatchRequest) -> SimilarBatchResponse:
    """Return similar vehicles for multiple vehicle IDs in one DB query. Supports 'rule-based' and 'semantic'.

    Per-vehicle `statuses` w response rozróżnia:
    - `pending` — pojazd nie ma embeddingów, on-demand task został zaplanowany
    - `ready`   — pojazd ma embeddingi, RPC zwrócił dopasowania
    - `empty`   — pojazd ma embeddingi, ale RPC zwrócił 0 dopasowań
    Frontend pokazuje "Trwa generowanie..." dla `pending`, obecny komunikat
    "Brak podobnych" dla `empty`, pełną listę dla `ready`.
    """

    params_hash = _params_hash(req.model_dump_json())
    cache_key = f"{_PREFIX}batch_similar_v2:{params_hash}"

    cached = _redis_get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT: batch-similar [%s]", params_hash)

        # Odbudowa ze słownika
        restored_results: dict[str, list[SimilarVehicleMatch]] = {}
        for vid, cars in cached.get("results", {}).items():
            restored_results[vid] = [SimilarVehicleMatch(**c) for c in cars]

        cached_statuses = cached.get("statuses") or {}
        return SimilarBatchResponse(results=restored_results, statuses=cached_statuses)

    # Service-role client: anon's 3s statement_timeout cancels semantic RPCs on cold cache
    sb = get_admin_client()
    method = (
        "rpc_get_similar_vehicles_batch_semantic"
        if req.mode == "semantic"
        else "rpc_get_similar_vehicles_batch"
    )

    try:
        if not req.vehicle_ids:
            return SimilarBatchResponse(results={}, statuses={})

        # Pre-check: dla których pojazdów źródłowych brakuje embeddingów?
        # Te są oznaczane jako `pending` i on-demand task triggerowany (z dedupe).
        # RPC i tak zwróci puste dla nich, więc filtrujemy żeby nie marnować
        # czasu RPC i zwracamy szybciej z `pending`.
        statuses: dict[str, str] = {vid: "ready" for vid in req.vehicle_ids}
        pending_ids: set[str] = set()
        try:
            pre_resp = _supabase_execute_with_retry(
                sb.table("vehicle_synthesis")
                .select("id, semantic_embedding, vector_use_case, vector_specs, vector_equipment")
                .in_("id", req.vehicle_ids)
            )
            for v_row in (pre_resp.data or []):
                vid = str(v_row["id"])
                missing = any(
                    v_row.get(col) is None
                    for col in ("semantic_embedding", "vector_use_case", "vector_specs", "vector_equipment")
                )
                if missing:
                    pending_ids.add(vid)
                    statuses[vid] = "pending"
                    _enqueue_embedding_with_dedupe(vid)
        except Exception as exc:
            logger.debug("batch-similar pre-check failed: %s", exc)

        # Wywołaj RPC tylko dla pojazdów które MAJĄ embeddingi.
        # Te w `pending` zostawiamy z pustą listą + status `pending`.
        rpc_ids = [vid for vid in req.vehicle_ids if vid not in pending_ids]
        response = _supabase_execute_with_retry(
            sb.rpc(
                method,
                {
                    "p_vehicle_ids": rpc_ids,
                    "p_limit": req.limit,
                    "p_duration_months": req.duration_months,
                    "p_annual_mileage": req.annual_mileage,
                    "p_requirements": [r.model_dump() for r in req.requirements]
                    if req.requirements
                    else [],
                },
            )
        ) if rpc_ids else type("EmptyResp", (), {"data": []})()

        results: dict[str, list[SimilarVehicleMatch]] = {
            vid: [] for vid in req.vehicle_ids
        }

        if response.data:
            from typing import cast, Any

            rows = cast(list[dict[str, Any]], response.data)

            # Fallback: RPC reads drive_type from card_summary.drivetrain (often null).
            # Bulk-fetch mapped_ai_data.drive_type for candidates that came back "N/A"
            # so the spec chip ("FWD" / "AWD" / "RWD") shows up next to body/engine/gearbox.
            missing_drive_ids = {
                str(r.get("vehicle_id"))
                for r in rows
                if not r.get("drive_type") or str(r.get("drive_type")).upper() in {"N/A", "NULL", ""}
            }
            drive_lookup: dict[str, str] = {}
            if missing_drive_ids:
                try:
                    drive_resp = _supabase_execute_with_retry(
                        sb.table("vehicle_synthesis")
                        .select("id,synthesis_data")
                        .in_("id", list(missing_drive_ids))
                    )
                    for v_row in (drive_resp.data or []):
                        sd = v_row.get("synthesis_data") or {}
                        m = sd.get("mapped_ai_data") or {}
                        raw = m.get("drive_type")
                        normalized = _normalize_drive_type(raw) or (str(raw).strip() if raw else None)
                        if normalized:
                            drive_lookup[str(v_row["id"])] = normalized
                except Exception as exc:
                    logger.debug("drive_type fallback lookup failed: %s", exc)

            for row in rows:
                vid = str(row.get("vehicle_id"))
                if vid in drive_lookup:
                    row["drive_type"] = drive_lookup[vid]
                else:
                    # Normalize whatever the RPC returned (e.g. "Quattro" → "AWD").
                    norm = _normalize_drive_type(row.get("drive_type"))
                    if norm:
                        row["drive_type"] = norm
                source_id = str(row.pop("source_vehicle_id"))
                match = _build_similar_vehicle_match(row)
                if source_id in results:
                    results[source_id].append(match)

        # Enrich every match with the snapshot of its candidate kalkulacja in a
        # single round-trip across all source-buckets so each similar-card has
        # the rabat/opony/insurance/replacement-car/WIBOR row the user expects
        # next to a price.
        all_matches = [m for bucket in results.values() for m in bucket]
        _attach_kalkulacja_snapshot_to_matches(all_matches)

        # Dopinguj statusy: jeśli pojazd ma embeddingi ALE RPC nie zwrócił
        # żadnych dopasowań → "empty" (uczciwy "Brak podobnych pojazdów").
        # Pozostałe nie-pending z dopasowaniami → "ready".
        for vid in req.vehicle_ids:
            if statuses.get(vid) == "pending":
                continue
            statuses[vid] = "ready" if results.get(vid) else "empty"

        resp_obj = SimilarBatchResponse(results=results, statuses=statuses)

        # Serialize fully using model dumps for the cache
        serialized_results: dict[str, Any] = {}
        for k, v in results.items():
            serialized_results[k] = [m.model_dump() for m in v]

        _redis_set(
            cache_key,
            {"results": serialized_results, "statuses": statuses},
            _TTL_SEARCH,
        )

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
    # Service-role client: anon's 3s statement_timeout cancels this RPC on larger batches
    sb = get_admin_client()

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
        # Pull the per-kalkulacja snapshot (rabat / marża bankowa / WIBOR /
        # toggle-set) in a single round-trip so each price below carries the
        # context the user needs to interpret it.
        snapshot_by_kid = _fetch_kalkulacja_snapshot_params(
            [r.get("kalkulacja_id") for r in rows if r.get("kalkulacja_id")]
        )
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

            kid = row.get("kalkulacja_id")
            snap = snapshot_by_kid.get(str(kid)) if kid else None
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
                kalkulacja_id=kid,
                **(snap or {}),
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
    kalkulacja_id: Optional[str] = None,
) -> PriceForParamsResponse:
    """Return the LTR price tile based exclusively on historical cache.

    When `kalkulacja_id` is provided, the result is constrained to that specific
    calculation (used by pinned-calculation cards in the search). Otherwise the
    function falls back to the user-selected calc, then the newest one.
    """
    sb = supabase
    try:
        query = (
            sb.table("vehicle_matrix_cache")
            .select(
                "duration_months, annual_mileage, monthly_price_net, calculated_at, kalkulacja_id, tire_class, service_type"
            )
            .eq("vehicle_id", vehicle_id)
            .eq("duration_months", duration_months)
            .eq("annual_mileage", annual_mileage)
        )
        if kalkulacja_id:
            query = query.eq("kalkulacja_id", kalkulacja_id)
        resp = query.execute()
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

        kid_best = best_match.get("kalkulacja_id")
        snap = (
            _fetch_kalkulacja_snapshot_params([kid_best]).get(str(kid_best))
            if kid_best
            else None
        )

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
            kalkulacja_id=kid_best,
            **(snap or {}),
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
    kalkulacja_id: Optional[str] = None,
) -> list[PriceForParamsResponse]:
    """Return the LTR price variants for all standard durations at a given annual mileage.

    When `kalkulacja_id` is provided, only variants from that specific calculation
    are returned (used by pinned-calculation cards in the search).
    """
    sb = supabase
    try:
        query = (
            sb.table("vehicle_matrix_cache")
            .select(
                "duration_months, annual_mileage, monthly_price_net, "
                "kalkulacja_id, tire_class, service_type, calculated_at"
            )
            .eq("vehicle_id", vehicle_id)
            .eq("annual_mileage", annual_mileage)
            .in_("duration_months", [24, 36, 48, 60])
        )
        if kalkulacja_id:
            query = query.eq("kalkulacja_id", kalkulacja_id)
        resp = query.execute()
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
                        # Carry kalkulacja_id through so the cart can recover the
                        # full LTR breakdown (fin/tech split, in_rate, options)
                        # when the user adds a variant to the offer.
                        "kalkulacja_id": row.get("kalkulacja_id"),
                        "tire_class": row.get("tire_class"),
                        "service_type": row.get("service_type"),
                        "calculated_at": row.get("calculated_at"),
                    }

        snapshot_by_kid = _fetch_kalkulacja_snapshot_params(
            [v.get("kalkulacja_id") for v in grouped_variants.values() if v.get("kalkulacja_id")]
        )
        variants = [
            PriceForParamsResponse(
                vehicle_id=vehicle_id,
                duration_months=v["duration_months"],
                annual_mileage=v["annual_mileage"],
                monthly_price_net=v["monthly_price_net"],
                found=True,
                kalkulacja_id=v.get("kalkulacja_id"),
                tire_class=v.get("tire_class"),
                service_type=v.get("service_type"),
                calculated_at=v.get("calculated_at"),
                **(snapshot_by_kid.get(str(v.get("kalkulacja_id") or "")) or {}),
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


# ── Package decomposition (LLM-inferred sub-features per package) ─────────────


@router.get(
    "/scoring-search/vehicle/{vehicle_id}/package-contents",
    response_model=PackageContentsResponse,
)
def get_vehicle_package_contents(vehicle_id: str) -> PackageContentsResponse:
    """Return LLM-decomposed sub-features grouped by parent package.

    Thin wrapper over `feature_enrichment.fetch_package_contents()` — the same
    helper is reused by the offer-XLS generator to render expandable package
    rows.
    """
    from core.feature_enrichment import fetch_package_contents

    try:
        raw = fetch_package_contents(vehicle_id)
    except Exception as e:
        logger.exception("Error fetching package contents [%s]: %s", vehicle_id, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch package contents: {e}"
        )

    packages: dict[str, list[PackageSubFeature]] = {
        pkg: [PackageSubFeature(feature_name=n, confidence=c) for n, c in subs]
        for pkg, subs in raw.items()
    }
    return PackageContentsResponse(vehicle_id=vehicle_id, packages=packages)


# ── Comparison-chart snapshot ─────────────────────────────────────────────────


def _row_to_snapshot(row: dict[str, Any], vehicle_id: str, error: str | None = None) -> VehicleSnapshot:
    """Map a `vehicle_matrix_cache` row to a VehicleSnapshot.

    Falls back to error="null_decomposition" when the row exists but the
    breakdown columns are NULL (pre-backfill state). monthly_total stays usable
    because monthly_price_net is always present on the row.
    """
    months = int(row.get("duration_months") or 0) or None
    mileage = int(row.get("annual_mileage") or 0) or None
    base_price_net = float(row["base_price_net"]) if row.get("base_price_net") is not None else None
    monthly_total = float(row["monthly_price_net"]) if row.get("monthly_price_net") is not None else None
    utrata = row.get("utrata_wartosci_pln")
    serwis = row.get("koszty_serwisowe_pln")
    opony = row.get("koszt_opon_pln")
    ubezp = row.get("ubezpieczenie_pln")
    wr_pct = row.get("wr_pct")

    has_decomposition = any(v is not None for v in (utrata, serwis, opony, ubezp))
    effective_error = error or (None if has_decomposition else "null_decomposition")

    def per_month(total: Any) -> Optional[float]:
        if total is None or not months:
            return None
        return round(float(total) / months, 2)

    return VehicleSnapshot(
        vehicle_id=vehicle_id,
        found=True,
        duration_months=months,
        annual_mileage=mileage,
        base_price_net=base_price_net,
        wr_pct=float(wr_pct) if wr_pct is not None else None,
        wr_pln=float(utrata) if utrata is not None else None,
        monthly_amortization=per_month(utrata),
        monthly_service=per_month(serwis),
        monthly_tires=per_month(opony),
        monthly_insurance=per_month(ubezp),
        monthly_total=monthly_total,
        error=effective_error,
    )


def _row_to_curve_point(row: dict[str, Any]) -> WrCurvePoint:
    return WrCurvePoint(
        duration_months=int(row["duration_months"]),
        wr_pct=float(row["wr_pct"]) if row.get("wr_pct") is not None else None,
        wr_pln=float(row["utrata_wartosci_pln"]) if row.get("utrata_wartosci_pln") is not None else None,
        monthly_total=float(row["monthly_price_net"]) if row.get("monthly_price_net") is not None else None,
    )


def _pick_latest_per_duration(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Deduplicate by duration_months, keeping the most recently calculated row.

    `vehicle_matrix_cache` can hold several rows per (duration, mileage) when
    multiple kalkulacje exist for the same vehicle, or when margin_pct varies.
    We pick the one with the newest `calculated_at` so the snapshot matches the
    list view's "latest kalkulacja" semantics.
    """
    out: dict[int, dict[str, Any]] = {}
    for r in rows:
        dur = int(r.get("duration_months") or 0)
        if not dur:
            continue
        prev = out.get(dur)
        if prev is None:
            out[dur] = r
            continue
        if str(r.get("calculated_at") or "") > str(prev.get("calculated_at") or ""):
            out[dur] = r
    return out


def _build_snapshot_for_vehicle(
    rows: list[dict[str, Any]],
    vehicle_id: str,
    target_months: int,
    include_curve: bool,
) -> VehicleSnapshot:
    if not rows:
        return VehicleSnapshot(vehicle_id=vehicle_id, found=False, error="not_in_cache")

    by_duration = _pick_latest_per_duration(rows)
    if not by_duration:
        return VehicleSnapshot(vehicle_id=vehicle_id, found=False, error="not_in_cache")

    exact = by_duration.get(target_months)
    snap_error: Optional[str] = None
    if exact is None:
        nearest_dur = min(by_duration.keys(), key=lambda d: abs(d - target_months))
        exact = by_duration[nearest_dur]
        snap_error = "snap_to_nearest"

    snapshot = _row_to_snapshot(exact, vehicle_id, error=snap_error)

    if include_curve:
        curve = [_row_to_curve_point(by_duration[d]) for d in sorted(by_duration.keys())]
        snapshot = snapshot.model_copy(update={"wr_curve": curve})

    return snapshot


def _fetch_snapshot_rows(vehicle_ids: list[str], annual_mileage: int) -> list[dict[str, Any]]:
    """Single SELECT pulling every cache row needed for the snapshot view."""
    res = (
        supabase.table("vehicle_matrix_cache")
        .select(
            "vehicle_id, duration_months, annual_mileage, base_price_net, "
            "monthly_price_net, utrata_wartosci_pln, koszty_serwisowe_pln, "
            "koszt_opon_pln, ubezpieczenie_pln, wr_pct, calculated_at"
        )
        .in_("vehicle_id", vehicle_ids)
        .eq("annual_mileage", annual_mileage)
        .execute()
    )
    return list(res.data or [])


@router.post(
    "/scoring-search/comparison-snapshot",
    response_model=ComparisonSnapshotResponse,
)
def get_comparison_snapshot(req: ComparisonSnapshotRequest) -> ComparisonSnapshotResponse:
    """Pre-computed cost decomposition for a small set of vehicles.

    Powers the comparison-chart view's pinned panel and the per-card hover.
    Backed entirely by `vehicle_matrix_cache` — no LTRKalkulator invocation,
    so latency is one Postgres SELECT regardless of the vehicle count (≤8).
    """
    rows = _fetch_snapshot_rows(req.vehicle_ids, req.annual_mileage)
    rows_by_vehicle: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        rows_by_vehicle.setdefault(str(r.get("vehicle_id")), []).append(r)

    snapshots: dict[str, VehicleSnapshot] = {}
    for vid in req.vehicle_ids:
        snapshots[vid] = _build_snapshot_for_vehicle(
            rows_by_vehicle.get(vid, []),
            vehicle_id=vid,
            target_months=req.months,
            include_curve=req.include_curve,
        )

    return ComparisonSnapshotResponse(snapshots=snapshots)


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
