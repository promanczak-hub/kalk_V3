"""MDM (Master Data Management) models for the Agnostic Feature System.

Defines Pydantic models for:
- Feature dictionary entries (universal_features MDM columns)
- Tender Engine criteria and results
- Vehicle specs normalized responses
"""

from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FeatureTier(str, Enum):
    """Classification tier controlling extraction priority and UI visibility."""

    CORE = "CORE"
    EXTENDED = "EXTENDED"
    EDGE = "EDGE"


class TenderPriority(str, Enum):
    """Priority level for tender criteria."""

    MUST = "MUST"
    SHOULD = "SHOULD"
    NICE = "NICE"


class ComplianceStatus(str, Enum):
    """Result status for a single tender criterion evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"


class VehicleComplianceStatus(str, Enum):
    """Aggregate compliance status for a vehicle."""

    MATCH = "MATCH"
    NOT_COMPLIANT = "NOT_COMPLIANT"
    MISSING_DATA = "MISSING_DATA"


class SourceDocumentType(str, Enum):
    """Source provenance for extracted feature values."""

    CONFIG = "config"
    PRICELIST = "pricelist"
    BROCHURE = "brochure"
    ENRICHMENT = "enrichment"
    MANUAL = "manual"
    LLM_INFERENCE = "llm_inference"


# ---------------------------------------------------------------------------
# MDM Feature Definition (Excel ↔ DB sync)
# ---------------------------------------------------------------------------


class MDMFeatureDefinition(BaseModel):
    """Single feature row from the Master Dictionary (Google Sheet).

    Maps 1:1 to a row in `reverse_search.universal_features`.
    """

    technical_key: str = Field(
        ..., description="Unique English key from Excel (e.g. dim_length_mm)"
    )
    functional_name: str = Field(
        ..., description="Human-readable name (e.g. Długość pojazdu)"
    )
    data_type: Literal["bool", "int", "float", "enum"] = Field(
        ..., description="Value type for validation and UI rendering"
    )
    unit_source: str | None = None
    unit_target: str | None = None
    transformation_rule: str | None = None
    trigger_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords for AI extraction matching",
    )
    visibility_group: str = "Common"
    body_context: str = "ALL"
    is_tender_criteria: bool = False
    required_for_tender: bool = False
    feature_tier: FeatureTier = FeatureTier.EXTENDED
    is_filterable: bool = False
    is_contextual: bool = False
    is_mandatory_for_matching: bool = False
    is_comparable: bool = False
    is_derived: bool = False
    data_confidence_required: bool = False
    fallback_source: str | None = None


# ---------------------------------------------------------------------------
# Tender Engine
# ---------------------------------------------------------------------------


class TenderCriterion(BaseModel):
    """Single tender requirement — both UI-built and Excel-imported."""

    feature_key: str = Field(
        ..., description="technical_key or feature_key to evaluate"
    )
    operator: Literal[">=", "<=", ">", "<", "=", "!=", "IN"] = Field(
        ..., description="Comparison operator"
    )
    value: float | str | bool | list[str] = Field(
        ..., description="Required value or list for IN operator"
    )
    priority: TenderPriority = TenderPriority.MUST


class TenderEvaluateRequest(BaseModel):
    """Request body for POST /api/tender/evaluate."""

    criteria: list[TenderCriterion] = Field(
        ..., min_length=1, description="List of tender requirements"
    )
    vehicle_ids: list[UUID] | None = Field(
        None, description="Specific vehicles to evaluate. None = all fleet."
    )


class CriterionResult(BaseModel):
    """Evaluation result for a single criterion against a vehicle."""

    feature_key: str
    feature_name: str | None = None
    required_operator: str
    required_value: str
    actual_value: float | str | bool | None = None
    status: ComplianceStatus
    source: str | None = None
    confidence: float | None = None


class VehicleTenderResult(BaseModel):
    """Aggregate tender result for a single vehicle."""

    vehicle_id: UUID
    vehicle_label: str = ""
    compliance_status: VehicleComplianceStatus
    compliance_score: float = Field(
        ..., ge=0.0, le=1.0, description="0.0-1.0 weighted compliance"
    )
    criteria_results: list[CriterionResult] = Field(default_factory=list)
    must_pass_count: int = 0
    must_fail_count: int = 0
    should_pass_count: int = 0
    nice_pass_count: int = 0


class TenderEvaluateResponse(BaseModel):
    """Response for POST /api/tender/evaluate."""

    total_vehicles: int
    match_count: int
    not_compliant_count: int
    missing_data_count: int
    results: list[VehicleTenderResult]


# ---------------------------------------------------------------------------
# Vehicle Specs Normalized (API responses)
# ---------------------------------------------------------------------------


class VehicleSpecValue(BaseModel):
    """Single spec entry for a vehicle."""

    feature_key: str
    feature_name: str
    category: str | None = None
    feature_tier: FeatureTier | None = None
    value_numeric: float | None = None
    value_text: str | None = None
    value_bool: bool | None = None
    unit: str | None = None
    source: str | None = None
    confidence: float | None = None
    needs_review: bool = False


class VehicleSpecsResponse(BaseModel):
    """Full specs for a vehicle, grouped by visibility."""

    vehicle_id: UUID
    vehicle_label: str = ""
    total_specs: int = 0
    core_specs: list[VehicleSpecValue] = Field(default_factory=list)
    extended_specs: list[VehicleSpecValue] = Field(default_factory=list)
    edge_specs: list[VehicleSpecValue] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Feature Dictionary (for frontend rendering)
# ---------------------------------------------------------------------------


class FeatureDictionaryEntry(BaseModel):
    """Single entry in the feature dictionary sent to frontend."""

    id: str
    feature_key: str
    technical_key: str | None = None
    display_name: str
    category: str | None = None
    feature_type: str
    feature_tier: FeatureTier | None = None
    canonical_unit: str | None = None
    is_filterable: bool = False
    is_tender_criteria: bool = False
    is_comparable: bool = False
    body_context: str = "ALL"
    visibility_group: str | None = None
