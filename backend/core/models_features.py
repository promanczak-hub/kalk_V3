"""Pydantic models for the reverse_search / universal features system."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────


class FeatureType(str, Enum):
    BOOLEAN = "boolean"
    NUMERIC = "numeric"
    ENUM = "enum"
    TEXT = "text"


class VehicleScope(str, Enum):
    PASSENGER = "passenger"
    COMMERCIAL = "commercial"
    BOTH = "both"


class ResolvedStatus(str, Enum):
    PRESENT_CONFIRMED_PRIMARY = "present_confirmed_primary"
    PRESENT_CONFIRMED_SECONDARY = "present_confirmed_secondary"
    PRESENT_INFERRED = "present_inferred"
    OPTIONAL_PACKAGE_POSSIBLE = "optional_package_possible"
    AVAILABLE_FOR_CONFIGURATION = "available_for_configuration"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    CONTRADICTION_DETECTED = "contradiction_detected"


class EvidenceSourceType(str, Enum):
    SPEC = "spec"
    VARIANT_DOC = "variant_doc"
    CATALOG = "catalog"
    BROCHURE = "brochure"
    PRICE_LIST = "price_list"
    EXCEL_IMPORT = "excel_import"
    SERVICE_OPTION = "service_option"
    BODY_PARAMETERS = "body_parameters"
    MANUAL_OVERRIDE = "manual_override"
    LLM_INFERENCE = "llm_inference"


class EvidenceStatus(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    OPTIONAL = "optional"
    NOT_FOUND = "not_found"
    NOT_APPLICABLE = "not_applicable"
    CONFLICT = "conflict"


class DocumentRole(str, Enum):
    PRIMARY_SPEC = "primary_spec"
    VARIANT_DOC = "variant_doc"
    CATALOG = "catalog"
    BROCHURE = "brochure"
    PRICE_LIST = "price_list"
    FLEET_STANDARD = "fleet_standard"


# ── Category ───────────────────────────────────────────────────


class UniversalFeatureCategory(BaseModel):
    id: UUID | None = None
    category_key: str
    display_name: str
    vehicle_scope: VehicleScope = VehicleScope.BOTH
    sort_order: int = 100
    is_active: bool = True


# ── Feature ────────────────────────────────────────────────────


class UniversalFeature(BaseModel):
    id: UUID | None = None
    feature_key: str
    display_name: str
    category_id: UUID
    feature_type: FeatureType
    canonical_unit: str | None = None
    vehicle_scope: VehicleScope = VehicleScope.BOTH
    is_filterable: bool = True
    is_visible_in_card_summary: bool = True
    is_visible_in_brochure: bool = True
    is_service_related: bool = False
    is_bodywork_related: bool = False
    is_required_for_reverse_search: bool = False
    source_standard: str = "fleet_excel"
    description: str | None = None
    sort_order: int = 100
    is_active: bool = True


class UniversalFeatureAlias(BaseModel):
    id: UUID | None = None
    feature_id: UUID
    alias_text: str
    normalized_alias: str
    source_type: str = "excel_import"
    brand: str | None = None
    language: str | None = "pl"
    is_active: bool = True


class UniversalFeatureEnumValue(BaseModel):
    id: UUID | None = None
    feature_id: UUID
    enum_key: str
    display_name: str
    sort_order: int = 100
    is_active: bool = True


# ── Evidence & State ───────────────────────────────────────────


class VehicleFeatureEvidence(BaseModel):
    id: UUID | None = None
    source_vehicle_id: UUID
    bundle_id: UUID | None = None
    feature_id: UUID
    document_id: UUID | None = None
    source_type: EvidenceSourceType
    evidence_status: EvidenceStatus = EvidenceStatus.OBSERVED
    source_text: str | None = None
    source_path: str | None = None
    value_bool: bool | None = None
    value_num: float | None = None
    value_text: str | None = None
    unit: str | None = None
    confidence: float | None = None
    priority_rank: int = 100


class VehicleFeatureState(BaseModel):
    id: UUID | None = None
    source_vehicle_id: UUID
    bundle_id: UUID | None = None
    feature_id: UUID
    resolved_status: ResolvedStatus
    resolved_value_bool: bool | None = None
    resolved_value_num: float | None = None
    resolved_value_text: str | None = None
    resolved_unit: str | None = None
    confidence: float | None = None
    resolution_source: str | None = None
    is_manual_override: bool = False


# ── Context Bundle ─────────────────────────────────────────────


class VehicleContextBundle(BaseModel):
    id: UUID | None = None
    source_vehicle_id: UUID
    bundle_name: str
    merge_strategy: str = "priority_merge"
    is_active: bool = True
    created_by: str | None = None


class VehicleContextBundleDocument(BaseModel):
    id: UUID | None = None
    bundle_id: UUID
    document_id: UUID | None = None
    document_role: DocumentRole
    priority_order: int = 100
    selected_by_user: bool = True
    notes: str | None = None


# ── API Request/Response Models ────────────────────────────────


class FeatureFilterItem(BaseModel):
    """Single filter criterion for reverse search."""

    feature_key: str
    value_bool: bool | None = None
    value_num_min: float | None = None
    value_num_max: float | None = None
    value_text: str | None = None


class FeatureSearchRequest(BaseModel):
    """Reverse search request payload."""

    filters: list[FeatureFilterItem] = Field(default_factory=list)
    vehicle_scope: VehicleScope | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class FeatureSearchResultItem(BaseModel):
    """Single vehicle in search results."""

    source_vehicle_id: UUID
    brand: str | None = None
    model: str | None = None
    matched_features: int = 0
    total_filters: int = 0
    match_score: float = 0.0


class FeatureSearchResponse(BaseModel):
    """Reverse search response."""

    results: list[FeatureSearchResultItem] = Field(
        default_factory=list,
    )
    total_count: int = 0


class FeatureCatalogResponse(BaseModel):
    """Response for feature catalog listing."""

    categories: list[dict[str, Any]] = Field(default_factory=list)
    total_features: int = 0


class FeatureImportResult(BaseModel):
    """Result of Excel feature import."""

    import_run_id: UUID | None = None
    categories_created: int = 0
    features_created: int = 0
    features_updated: int = 0
    aliases_created: int = 0
    enum_values_created: int = 0
    errors: list[str] = Field(default_factory=list)
