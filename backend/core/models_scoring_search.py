from typing import Any, List, Optional
from pydantic import BaseModel, Field

class ScoringRequirement(BaseModel):
    feature_key: str
    operator: str = Field(description="'eq', 'gte', 'lte', 'in'")
    value: Any = Field(description="The target value to match against")
    requirement: str = Field(description="'MUST_HAVE' or 'NICE_TO_HAVE'")
    weight: float = Field(default=1.0, description="Weight of the requirement for scoring")
    values: Optional[List[Any]] = Field(default=None, description="List of values for 'in' operator")

class ScoringSearchRequest(BaseModel):
    brands: Optional[List[str]] = None
    models: Optional[List[str]] = None
    samar_class_ids: Optional[List[int]] = None
    requirements: List[ScoringRequirement]
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

class ScoringSearchResponse(BaseModel):
    results: List[ScoringSearchMatch]
    total_count: int

class AvailableFiltersRequest(BaseModel):
    brands: Optional[List[str]] = None
    models: Optional[List[str]] = None
    samar_class_ids: Optional[List[int]] = None
    current_filters: Optional[dict[str, Any]] = None

class InitialDataResponse(BaseModel):
    brands: List[str]
    models: List[str]
    brand_model_map: dict[str, List[str]]
    brand_counts: dict[str, int] = {}
    samar_classes: List[dict[str, Any]]
