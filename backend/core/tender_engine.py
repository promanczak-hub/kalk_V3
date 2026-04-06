"""Tender Engine — multi-criteria vehicle compliance evaluation.

Supports two input modes:
- UI-built criteria (JSON from frontend)
- Excel-uploaded criteria (parsed by tender_excel_parser.py)

Both modes produce identical TenderEvaluateRequest payloads.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from supabase import Client

from backend.core.mdm_models import (
    ComplianceStatus,
    CriterionResult,
    TenderCriterion,
    TenderEvaluateRequest,
    TenderEvaluateResponse,
    TenderPriority,
    VehicleComplianceStatus,
    VehicleTenderResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------


def _evaluate_single_criterion(
    criterion: TenderCriterion,
    actual_value: float | str | bool | None,
) -> ComplianceStatus:
    """Compare actual value against criterion requirement.

    Returns PASS, FAIL, or MISSING based on operator and value.
    """
    if actual_value is None:
        return ComplianceStatus.MISSING

    op = criterion.operator
    required = criterion.value

    if op == "IN":
        if not isinstance(required, list):
            required = [str(required)]
        return (
            ComplianceStatus.PASS
            if str(actual_value).upper() in [v.upper() for v in required]
            else ComplianceStatus.FAIL
        )

    # Numeric comparisons
    try:
        actual_num = float(actual_value)
        required_num = float(required)
    except (ValueError, TypeError):
        # String/bool comparison
        if op == "=":
            return (
                ComplianceStatus.PASS
                if str(actual_value).upper() == str(required).upper()
                else ComplianceStatus.FAIL
            )
        if op == "!=":
            return (
                ComplianceStatus.PASS
                if str(actual_value).upper() != str(required).upper()
                else ComplianceStatus.FAIL
            )
        logger.warning(
            "Cannot compare non-numeric values with operator %s: "
            "actual=%s, required=%s",
            op,
            actual_value,
            required,
        )
        return ComplianceStatus.FAIL

    comparisons: dict[str, bool] = {
        ">=": actual_num >= required_num,
        "<=": actual_num <= required_num,
        ">": actual_num > required_num,
        "<": actual_num < required_num,
        "=": actual_num == required_num,
        "!=": actual_num != required_num,
    }

    passed = comparisons.get(op, False)
    return ComplianceStatus.PASS if passed else ComplianceStatus.FAIL


def _calculate_compliance_score(
    results: list[CriterionResult],
    criteria: list[TenderCriterion],
) -> tuple[float, VehicleComplianceStatus, int, int, int, int]:
    """Calculate weighted compliance score.

    Weights: MUST=3, SHOULD=2, NICE=1.
    Any MUST FAIL → NOT_COMPLIANT.
    Any MISSING in MUST → MISSING_DATA.
    """
    weights = {
        TenderPriority.MUST: 3.0,
        TenderPriority.SHOULD: 2.0,
        TenderPriority.NICE: 1.0,
    }

    total_weight = 0.0
    earned_weight = 0.0
    must_fail = 0
    must_pass = 0
    should_pass = 0
    nice_pass = 0
    has_must_missing = False

    for criterion, result in zip(criteria, results, strict=True):
        w = weights[criterion.priority]
        total_weight += w

        if result.status == ComplianceStatus.PASS:
            earned_weight += w
            if criterion.priority == TenderPriority.MUST:
                must_pass += 1
            elif criterion.priority == TenderPriority.SHOULD:
                should_pass += 1
            else:
                nice_pass += 1
        elif result.status == ComplianceStatus.FAIL:
            if criterion.priority == TenderPriority.MUST:
                must_fail += 1
        elif result.status == ComplianceStatus.MISSING:
            if criterion.priority == TenderPriority.MUST:
                has_must_missing = True

    score = earned_weight / total_weight if total_weight > 0 else 0.0

    if must_fail > 0:
        status = VehicleComplianceStatus.NOT_COMPLIANT
    elif has_must_missing:
        status = VehicleComplianceStatus.MISSING_DATA
    else:
        status = VehicleComplianceStatus.MATCH

    return score, status, must_pass, must_fail, should_pass, nice_pass


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _resolve_feature_keys(
    sb: Client,
    criteria: list[TenderCriterion],
) -> dict[str, dict[str, Any]]:
    """Map feature_key/technical_key to feature metadata.

    Returns dict keyed by criterion.feature_key with:
    - feature_id (UUID)
    - display_name
    - feature_type
    """
    keys = [c.feature_key for c in criteria]

    result = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key, technical_key, display_name, feature_type")
        .or_(
            ",".join(
                [f"feature_key.eq.{k}" for k in keys]
                + [f"technical_key.eq.{k}" for k in keys]
            )
        )
        .execute()
    )

    mapping: dict[str, dict[str, Any]] = {}
    for row in result.data:
        for key_field in ("feature_key", "technical_key"):
            if row.get(key_field) and row[key_field] in keys:
                mapping[row[key_field]] = {
                    "feature_id": row["id"],
                    "display_name": row["display_name"],
                    "feature_type": row["feature_type"],
                }
    return mapping


def _get_vehicle_specs(
    sb: Client,
    vehicle_ids: list[UUID] | None,
    feature_ids: list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Fetch specs_normalized for vehicles keyed by vehicle_id → feature_id.

    Returns: {vehicle_id: {feature_id: {value_numeric, value_text, ...}}}
    """
    query = (
        sb.schema("reverse_search")
        .table("vehicle_specs_normalized")
        .select(
            "vehicle_id, feature_id, value_numeric, value_text, value_bool, "
            "source_document_type, confidence_score"
        )
        .in_("feature_id", feature_ids)
    )

    if vehicle_ids:
        query = query.in_("vehicle_id", [str(v) for v in vehicle_ids])

    result = query.execute()

    specs: dict[str, dict[str, dict[str, Any]]] = {}
    for row in result.data:
        vid = row["vehicle_id"]
        fid = row["feature_id"]
        if vid not in specs:
            specs[vid] = {}
        specs[vid][fid] = row

    return specs


def _get_vehicle_labels(
    sb: Client,
    vehicle_ids: list[str],
) -> dict[str, str]:
    """Fetch human-readable labels for vehicles."""
    result = (
        sb.table("vehicle_synthesis")
        .select("id, brand, model")
        .in_("id", vehicle_ids)
        .execute()
    )
    return {
        row["id"]: f"{row.get('brand', '?')} {row.get('model', '?')}"
        for row in result.data
    }


def _extract_actual_value(
    spec_row: dict[str, Any] | None,
    feature_type: str,
) -> float | str | bool | None:
    """Extract the appropriate value from a spec row based on feature type."""
    if spec_row is None:
        return None

    if feature_type == "boolean":
        return spec_row.get("value_bool")
    if feature_type in ("numeric", "int", "float"):
        val = spec_row.get("value_numeric")
        return float(val) if val is not None else None
    if feature_type in ("enum", "text"):
        return spec_row.get("value_text")

    # Fallback: try all
    for field in ("value_numeric", "value_bool", "value_text"):
        if spec_row.get(field) is not None:
            return spec_row[field]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_tender(
    sb: Client,
    request: TenderEvaluateRequest,
) -> TenderEvaluateResponse:
    """Evaluate fleet vehicles against tender criteria.

    This is the main entry point for both UI and Excel-uploaded criteria.
    """
    logger.info(
        "Tender evaluation: %d criteria, vehicle_ids=%s",
        len(request.criteria),
        request.vehicle_ids,
    )

    # 1. Resolve feature keys → IDs
    feature_map = _resolve_feature_keys(sb, request.criteria)
    missing_keys = [
        c.feature_key for c in request.criteria if c.feature_key not in feature_map
    ]
    if missing_keys:
        logger.error(
            "Tender evaluation aborted: unknown feature keys: %s",
            missing_keys,
        )
        msg = f"Unknown feature keys: {missing_keys}"
        raise ValueError(msg)

    feature_ids = [feature_map[c.feature_key]["feature_id"] for c in request.criteria]

    # 2. Fetch specs for all relevant vehicles
    specs = _get_vehicle_specs(sb, request.vehicle_ids, feature_ids)

    # Get all vehicle IDs (from specs or explicitly requested)
    if request.vehicle_ids:
        all_vehicle_ids = [str(v) for v in request.vehicle_ids]
    else:
        # Get all vehicles from vehicle_synthesis
        all_vehicles = sb.table("vehicle_synthesis").select("id").execute()
        all_vehicle_ids = [row["id"] for row in all_vehicles.data]

    # 3. Get labels
    labels = _get_vehicle_labels(sb, all_vehicle_ids)

    # 4. Evaluate each vehicle
    results: list[VehicleTenderResult] = []

    for vid in all_vehicle_ids:
        vehicle_specs = specs.get(vid, {})
        criteria_results: list[CriterionResult] = []

        for criterion in request.criteria:
            fmeta = feature_map[criterion.feature_key]
            fid = fmeta["feature_id"]
            spec_row = vehicle_specs.get(fid)
            actual = _extract_actual_value(spec_row, fmeta["feature_type"])

            status = _evaluate_single_criterion(criterion, actual)

            criteria_results.append(
                CriterionResult(
                    feature_key=criterion.feature_key,
                    feature_name=fmeta["display_name"],
                    required_operator=criterion.operator,
                    required_value=str(criterion.value),
                    actual_value=actual,
                    status=status,
                    source=(spec_row.get("source_document_type") if spec_row else None),
                    confidence=(
                        float(spec_row["confidence_score"])
                        if spec_row and spec_row.get("confidence_score")
                        else None
                    ),
                )
            )

        score, compliance, must_p, must_f, should_p, nice_p = (
            _calculate_compliance_score(criteria_results, request.criteria)
        )

        results.append(
            VehicleTenderResult(
                vehicle_id=UUID(vid),
                vehicle_label=labels.get(vid, "Unknown"),
                compliance_status=compliance,
                compliance_score=round(score, 3),
                criteria_results=criteria_results,
                must_pass_count=must_p,
                must_fail_count=must_f,
                should_pass_count=should_p,
                nice_pass_count=nice_p,
            )
        )

    # 5. Sort: MATCH first, then by score descending
    results.sort(
        key=lambda r: (
            0 if r.compliance_status == VehicleComplianceStatus.MATCH else 1,
            -r.compliance_score,
        )
    )

    match_count = sum(
        1 for r in results if r.compliance_status == VehicleComplianceStatus.MATCH
    )
    not_compliant_count = sum(
        1
        for r in results
        if r.compliance_status == VehicleComplianceStatus.NOT_COMPLIANT
    )
    missing_count = sum(
        1
        for r in results
        if r.compliance_status == VehicleComplianceStatus.MISSING_DATA
    )

    return TenderEvaluateResponse(
        total_vehicles=len(results),
        match_count=match_count,
        not_compliant_count=not_compliant_count,
        missing_data_count=missing_count,
        results=results,
    )
