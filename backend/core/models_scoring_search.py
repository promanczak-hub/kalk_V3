from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ScoringRequirement(BaseModel):
    feature_key: str
    operator: str = Field(description="'eq', 'gte', 'lte', 'in'")
    value: Any = Field(description="The target value to match against")
    requirement: str = Field(description="'MUST_HAVE' or 'NICE_TO_HAVE'")
    weight: float = Field(
        default=1.0, description="Weight of the requirement for scoring"
    )
    values: Optional[List[Any]] = Field(
        default=None, description="List of values for 'in' operator"
    )


class ScoringSearchRequest(BaseModel):
    brands: Optional[List[str]] = None
    models: Optional[List[str]] = None
    trims: Optional[List[str]] = None
    samar_class_ids: Optional[List[int]] = None
    vehicle_ids: Optional[List[str]] = None
    requirements: List[ScoringRequirement]
    semantic_query: Optional[str] = None
    limit: int = 50
    offset: int = 0


class ScoringSearchMatch(BaseModel):
    vehicle_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    match_score_pct: float
    matched_features: List[str]
    missing_features: List[str]
    best_monthly_price: Optional[float] = None
    # Technical specification badges
    fuel_type: Optional[str] = None
    power_hp: Optional[int] = None
    transmission: Optional[str] = None
    body_style: Optional[str] = None
    drive_type: Optional[str] = None
    # Business / pricing badges
    base_price_gross: Optional[str] = None
    options_price_gross: Optional[str] = None
    total_price_gross: Optional[str] = None
    suggested_discount_pct: Optional[float] = None
    trim_level: Optional[str] = None
    vehicle_class: Optional[str] = None
    has_ltr_cache: Optional[bool] = None
    # Calculation parameters
    service_cost_type: Optional[str] = None
    tire_class: Optional[str] = None
    offer_number: Optional[str] = None
    configuration_code: Optional[str] = None


class ScoringSearchResponse(BaseModel):
    results: List[ScoringSearchMatch]
    total_count: int


class AvailableFiltersRequest(BaseModel):
    brands: Optional[List[str]] = None
    models: Optional[List[str]] = None
    body_types: Optional[List[str]] = None
    samar_class_ids: Optional[List[int]] = None
    current_filters: Optional[dict[str, Any]] = None


class BodyTypeItem(BaseModel):
    name: str
    count: int


class InitialDataResponse(BaseModel):
    brands: List[str]
    models: List[str]
    brand_model_map: dict[str, List[str]]
    brand_counts: dict[str, int] = {}
    trim_level_map: dict[str, List[str]] = {}
    samar_classes: List[dict[str, Any]]
    body_types: List[BodyTypeItem] = []


class OptionItem(BaseModel):
    name: str
    count: int


class TrimsAndOptionsRequest(BaseModel):
    brands: Optional[List[str]] = None
    models: Optional[List[str]] = None


class TrimsAndOptionsResponse(BaseModel):
    trim_levels: List[OptionItem] = []
    standard_options: List[OptionItem] = []
    paid_options: List[OptionItem] = []


class SimilarityReasons(BaseModel):
    """Structured breakdown explaining WHY a vehicle is similar."""

    samar_match: bool = False
    body_match: bool = False
    fuel_match: bool = False
    drive_match: bool = False
    price_pct_diff: Optional[float] = None  # e.g. 4.2 — catalog price % difference
    samar_category: Optional[str] = None  # e.g. "C Niższa Średnia"
    body_style: Optional[str] = None  # e.g. "Sedan"


class SimilarVehicleMatch(BaseModel):
    vehicle_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    samar_category: Optional[str] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    best_monthly_price: Optional[float] = None
    image_url: Optional[str] = None
    similarity_score_pct: Optional[float] = None
    # Extended categorization metadata
    power_hp: Optional[int] = None
    body_style: Optional[str] = None
    vehicle_class: Optional[str] = None
    drive_type: Optional[str] = None
    # Similarity breakdown — why this vehicle is similar
    similarity_reasons: Optional[SimilarityReasons] = None


class PriceForParamsResponse(BaseModel):
    vehicle_id: str
    duration_months: Optional[int] = None
    annual_mileage: Optional[int] = None
    monthly_price_net: Optional[float] = None
    calculated_at: Optional[str] = None
    found: bool = False
    variants_count: Optional[int] = None
    tire_class: Optional[str] = None
    service_type: Optional[str] = None
    kalkulacja_id: Optional[str] = None


class SimilarBatchRequest(BaseModel):
    vehicle_ids: list[str]
    limit: int = 5
    duration_months: Optional[int] = None
    annual_mileage: Optional[int] = None
    mode: str = "rule-based"  # "rule-based" or "semantic"


class SimilarBatchItem(SimilarVehicleMatch):
    source_vehicle_id: str


class SimilarBatchResponse(BaseModel):
    results: dict[str, list[SimilarVehicleMatch]]
