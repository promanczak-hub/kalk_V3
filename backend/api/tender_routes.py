"""Tender Engine API routes.

Endpoints:
- POST /api/tender/evaluate — Evaluate fleet vs criteria (JSON)
- POST /api/tender/upload — Upload Excel/CSV with criteria
- GET  /api/tender/criteria — List available tender criteria features
- GET  /api/features/dictionary — Full MDM dictionary for frontend
- GET  /api/features/specs/{vehicle_id} — Vehicle specs by tier
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.database import get_supabase
from backend.core.mdm_models import (
    FeatureDictionaryEntry,
    FeatureTier,
    TenderEvaluateRequest,
    TenderEvaluateResponse,
    VehicleSpecsResponse,
    VehicleSpecValue,
)
from backend.core.tender_engine import evaluate_tender
from backend.core.tender_excel_parser import (
    parse_tender_csv,
    parse_tender_excel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tender", "features"])


# ---------------------------------------------------------------------------
# Tender Engine endpoints
# ---------------------------------------------------------------------------


@router.post("/tender/evaluate", response_model=TenderEvaluateResponse)
async def tender_evaluate(request: TenderEvaluateRequest) -> TenderEvaluateResponse:
    """Evaluate fleet vehicles against tender criteria.

    Accepts criteria built in UI or parsed from Excel upload.
    """
    sb = get_supabase()
    try:
        return evaluate_tender(sb, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/tender/upload", response_model=TenderEvaluateResponse)
async def tender_upload(
    file: UploadFile = File(...),
) -> TenderEvaluateResponse:
    """Upload Excel/CSV file with tender criteria and evaluate fleet.

    Supported formats: .csv, .xlsx
    CSV delimiter: semicolon (;)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    content = await file.read()

    if ext == ".csv":
        text = content.decode("utf-8-sig")
        request = parse_tender_csv(text)
    elif ext in (".xlsx", ".xls"):
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            request = parse_tender_excel(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Use .csv or .xlsx",
        )

    sb = get_supabase()
    try:
        return evaluate_tender(sb, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/tender/criteria")
async def tender_criteria() -> list[FeatureDictionaryEntry]:
    """List features available as tender criteria.

    Returns only features with is_tender_criteria=TRUE or feature_tier=CORE.
    """
    sb = get_supabase()

    result = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select(
            "id, feature_key, technical_key, display_name, "
            "feature_type, feature_tier, canonical_unit, "
            "is_filterable, is_tender_criteria, is_comparable, "
            "body_context"
        )
        .or_("is_tender_criteria.eq.true,feature_tier.eq.CORE")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )

    return [
        FeatureDictionaryEntry(
            id=str(row["id"]),
            feature_key=row["feature_key"],
            technical_key=row.get("technical_key"),
            display_name=row["display_name"],
            feature_type=row["feature_type"],
            feature_tier=row.get("feature_tier"),
            canonical_unit=row.get("canonical_unit"),
            is_filterable=row.get("is_filterable", False),
            is_tender_criteria=row.get("is_tender_criteria", False),
            is_comparable=row.get("is_comparable", False),
            body_context=row.get("body_context", "ALL"),
        )
        for row in result.data
    ]


# ---------------------------------------------------------------------------
# Feature Dictionary endpoint
# ---------------------------------------------------------------------------


@router.get("/features/dictionary")
async def features_dictionary(
    tier: FeatureTier | None = None,
    body_context: str | None = None,
) -> list[FeatureDictionaryEntry]:
    """Full MDM feature dictionary for frontend rendering.

    Optional filters:
    - tier: CORE, EXTENDED, EDGE
    - body_context: ALL, Van, Pickup, SUV, EV, etc.
    """
    sb = get_supabase()

    query = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select(
            "id, feature_key, technical_key, display_name, "
            "feature_type, feature_tier, canonical_unit, "
            "is_filterable, is_tender_criteria, is_comparable, "
            "body_context, metadata"
        )
        .eq("is_active", True)
        .order("sort_order")
    )

    if tier:
        query = query.eq("feature_tier", tier.value)
    if body_context:
        query = query.or_(f"body_context.eq.ALL,body_context.ilike.%{body_context}%")

    result = query.execute()

    return [
        FeatureDictionaryEntry(
            id=str(row["id"]),
            feature_key=row["feature_key"],
            technical_key=row.get("technical_key"),
            display_name=row["display_name"],
            feature_type=row["feature_type"],
            feature_tier=row.get("feature_tier"),
            canonical_unit=row.get("canonical_unit"),
            is_filterable=row.get("is_filterable", False),
            is_tender_criteria=row.get("is_tender_criteria", False),
            is_comparable=row.get("is_comparable", False),
            body_context=row.get("body_context", "ALL"),
            visibility_group=(row.get("metadata", {}) or {}).get("visibility_group"),
        )
        for row in result.data
    ]


# ---------------------------------------------------------------------------
# Vehicle Specs endpoint (Progressive Disclosure)
# ---------------------------------------------------------------------------


@router.get("/features/specs/{vehicle_id}", response_model=VehicleSpecsResponse)
async def vehicle_specs(vehicle_id: UUID) -> VehicleSpecsResponse:
    """Get all specs for a vehicle, grouped by feature tier.

    Used by the Progressive Disclosure UI:
    - Basic view: core_specs
    - Advanced view: core_specs + extended_specs
    - Technical view: all specs
    """
    sb = get_supabase()

    # Get vehicle label
    vehicle = (
        sb.table("vehicle_synthesis")
        .select("id, brand, model")
        .eq("id", str(vehicle_id))
        .maybe_single()
        .execute()
    )

    if not vehicle.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    label = f"{vehicle.data.get('brand', '?')} {vehicle.data.get('model', '?')}"

    # Get all specs with feature metadata
    specs_result = (
        sb.schema("reverse_search")
        .table("vehicle_specs_normalized")
        .select(
            "value_numeric, value_text, value_bool, "
            "source_document_type, confidence_score, needs_human_review, "
            "feature_id, "
            "reverse_search_universal_features:feature_id("
            "  feature_key, display_name, feature_tier, "
            "  canonical_unit, feature_type"
            ")"
        )
        .eq("vehicle_id", str(vehicle_id))
        .execute()
    )

    core: list[VehicleSpecValue] = []
    extended: list[VehicleSpecValue] = []
    edge: list[VehicleSpecValue] = []

    for row in specs_result.data:
        feature_meta = row.get("reverse_search_universal_features", {})
        if not feature_meta:
            continue

        spec = VehicleSpecValue(
            feature_key=feature_meta.get("feature_key", ""),
            feature_name=feature_meta.get("display_name", ""),
            feature_tier=feature_meta.get("feature_tier"),
            value_numeric=(
                float(row["value_numeric"])
                if row.get("value_numeric") is not None
                else None
            ),
            value_text=row.get("value_text"),
            value_bool=row.get("value_bool"),
            unit=feature_meta.get("canonical_unit"),
            source=row.get("source_document_type"),
            confidence=(
                float(row["confidence_score"])
                if row.get("confidence_score") is not None
                else None
            ),
            needs_review=row.get("needs_human_review", False),
        )

        tier = feature_meta.get("feature_tier", "EXTENDED")
        if tier == "CORE":
            core.append(spec)
        elif tier == "EDGE":
            edge.append(spec)
        else:
            extended.append(spec)

    return VehicleSpecsResponse(
        vehicle_id=vehicle_id,
        vehicle_label=label,
        total_specs=len(core) + len(extended) + len(edge),
        core_specs=core,
        extended_specs=extended,
        edge_specs=edge,
    )
