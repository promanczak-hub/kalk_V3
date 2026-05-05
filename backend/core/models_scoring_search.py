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
    # Auto-fit: when true and `monthly_budget` is present in requirements, the
    # backend sweeps `vehicle_matrix_cache` per candidate, picks the cheapest
    # variant of the latest kalkulacja, and computes the maximum margin that
    # still fits the budget. Result lands in `best_fit_variant` on each match.
    # Frontend sets this true after AI extraction when budget came out of the
    # user query but duration/mileage/margin were not explicitly stated.
    fit_to_budget: bool = False
    monthly_budget: Optional[float] = None
    # Cap on the auto-fitted margin so absurdly cheap base prices don't yield
    # 90%+ margins. Backend clamps `applied_margin_pct` to this when sweeping.
    auto_margin_cap_pct: float = 30.0


class OptionLineItem(BaseModel):
    name: str
    price_net: Optional[float] = None
    price_gross: Optional[float] = None
    category: Optional[str] = None


class KalkulacjaSnapshotParams(BaseModel):
    """Calculation parameters carried alongside any price coming out of
    `vehicle_matrix_cache`. These come from the parent `ltr_kalkulacje.stan_json`
    and let the UI show what was assumed when the rate was computed: discount,
    bank margin, WIBOR, and the toggle-set (tyres/insurance/replacement car/
    service). All variants of the same `kalkulacja_id` share these values, so
    they're attached at the kalkulacja level, not per matrix row.
    """

    discount_pct: Optional[float] = None       # rabat dealerski %
    bank_margin_pct: Optional[float] = None    # marża bankowa % (financing)
    wibor_pct: Optional[float] = None          # WIBOR rate %
    tires_included: Optional[bool] = None      # z_oponami
    tire_buyback: Optional[bool] = None        # odkup_opon_enabled
    insurance_included: Optional[bool] = None  # express_pays_insurance
    replacement_car: Optional[bool] = None     # replacement_car_enabled
    service_included: Optional[bool] = None    # include_servicing


class BestFitVariant(BaseModel):
    """Auto-fit snapshot — cheapest matrix variant of the latest kalkulacja,
    with margin maximized to just fit `monthly_budget`. Populated only when
    request.fit_to_budget=True and the vehicle has at least one matrix row."""

    duration_months: int
    annual_mileage: int
    base_price_net: float            # cache row's monthly_price_net (margin 0%)
    applied_margin_pct: float        # auto-fitted margin, clamped to cap
    monthly_price_net: float         # final rate = base / (1 - margin/100)
    fits_budget: bool                # True if monthly_price_net <= budget
    over_budget_pln: Optional[float] = None  # set when fits_budget=False
    kalkulacja_id: Optional[str] = None
    tire_class: Optional[str] = None
    service_type: Optional[str] = None
    variants_count: Optional[int] = None  # how many cache rows the sweep saw
    # Snapshot of the kalkulacja's pricing toggles + financing knobs (rabat,
    # marża bankowa, WIBOR, opony/ubezpieczenie/auto zastępcze/serwis).
    discount_pct: Optional[float] = None
    bank_margin_pct: Optional[float] = None
    wibor_pct: Optional[float] = None
    tires_included: Optional[bool] = None
    tire_buyback: Optional[bool] = None
    insurance_included: Optional[bool] = None
    replacement_car: Optional[bool] = None
    service_included: Optional[bool] = None


class ScoringSearchMatch(BaseModel):
    vehicle_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    match_score_pct: float
    matched_features: List[str]
    missing_features: List[str]
    best_monthly_price: Optional[float] = None
    applied_margin_pct: Optional[float] = None
    # Technical specification badges
    fuel_type: Optional[str] = None
    power_hp: Optional[int] = None
    transmission: Optional[str] = None
    body_style: Optional[str] = None
    drive_type: Optional[str] = None
    semantic_hit_reason: Optional[str] = None
    # Business / pricing badges
    base_price_net: Optional[float] = None
    base_price_gross: Optional[float] = None
    options_price_net: Optional[float] = None
    options_price_gross: Optional[float] = None
    factory_options_price_net: Optional[float] = None
    factory_options_price_gross: Optional[float] = None
    service_options_price_net: Optional[float] = None
    service_options_price_gross: Optional[float] = None
    factory_options: List[OptionLineItem] = []
    service_options: List[OptionLineItem] = []
    total_price_net: Optional[float] = None
    total_price_gross: Optional[float] = None
    price_domain: Optional[str] = "brutto"
    suggested_discount_pct: Optional[float] = None
    trim_level: Optional[str] = None
    vehicle_class: Optional[str] = None
    has_ltr_cache: Optional[bool] = None
    # Calculation parameters
    service_cost_type: Optional[str] = None
    tire_class: Optional[str] = None
    offer_number: Optional[str] = None
    configuration_code: Optional[str] = None
    # Engine + provenance metadata (shown on result card)
    engine_capacity: Optional[str] = None
    engine_designation: Optional[str] = None
    extraction_date: Optional[str] = None
    # User-pinned calculations (multi-select). Frontend renders one card per id;
    # empty list → fall back to a single default card.
    selected_kalkulacja_ids: List[str] = []
    # Auto-fit snapshot — populated only when request.fit_to_budget=True.
    best_fit_variant: Optional[BestFitVariant] = None


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
    equipment_match: bool = False
    is_same_brand: bool = False
    equipment_similarity_pct: Optional[float] = None
    price_pct_diff: Optional[float] = None  # catalog price % difference
    is_cheaper: Optional[bool] = None  # True if this vehicle is cheaper than source
    samar_category: Optional[str] = None  # e.g. "C Niższa Średnia"
    body_style: Optional[str] = None  # e.g. "Sedan"
    base_price: Optional[float] = None
    paid_options: Optional[Any] = None
    is_fallback_match: bool = False

    # ── Discount-aware fields (V2 — populated by RPC enrichment when available) ──
    discount_pct: Optional[float] = None  # candidate's offer discount % (0-100)
    final_price_net: Optional[float] = None  # candidate's price after discount
    final_price_pct_diff: Optional[float] = None  # % diff vs source FINAL price
    discount_pct_diff: Optional[float] = None  # candidate.disc_pct - source.disc_pct (pp)

    # ── Utility-features for delivery vehicles ──
    payload_kg: Optional[int] = None
    cargo_volume_m3: Optional[float] = None
    body_type: Optional[str] = None  # zabudowa: "Wywrotka" | "Plandeka" | "Izoterma" itp.

    # ── Apple-to-apple setup check ──
    # True when the candidate has the same (tire_class, service_type) as source
    # for the requested (duration, mileage). When False, best_monthly_price is null.
    setup_match: Optional[bool] = None
    source_tire_class: Optional[str] = None
    source_service_type: Optional[str] = None

    # ── Matrix params the rate was priced for (echoed RPC inputs) ──
    matched_duration_months: Optional[int] = None
    matched_annual_mileage: Optional[int] = None


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
    engine_label: Optional[str] = None
    body_style: Optional[str] = None
    vehicle_class: Optional[str] = None
    drive_type: Optional[str] = None
    price_domain: Optional[str] = "brutto"
    # Similarity breakdown — why this vehicle is similar
    similarity_reasons: Optional[SimilarityReasons] = None
    ai_label: Optional[str] = None
    # Cache row id matching the source's setup — lets the frontend add the
    # candidate to the cart with the same kalkulacja anchor as the source row.
    kalkulacja_id: Optional[str] = None
    # ── Catalog price breakdown (parity with ScoringSearchMatch / source card) ──
    # Populated by _build_similar_vehicle_match from raw paid_options +
    # service_equipment shipped via similarity_reasons. Lets the frontend
    # render the same Cena bazowa / Opcje fabryczne / Opcje serwisowe sections
    # the main result card shows.
    base_price_net: Optional[float] = None
    base_price_gross: Optional[float] = None
    factory_options_price_net: Optional[float] = None
    factory_options_price_gross: Optional[float] = None
    service_options_price_net: Optional[float] = None
    service_options_price_gross: Optional[float] = None
    factory_options: List[OptionLineItem] = []
    service_options: List[OptionLineItem] = []
    total_price_net: Optional[float] = None
    total_price_gross: Optional[float] = None


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
    # Snapshot of the kalkulacja's pricing toggles + financing knobs (rabat,
    # marża bankowa, WIBOR, opony/ubezpieczenie/auto zastępcze/serwis). Same
    # for every matrix variant under the same kalkulacja_id.
    discount_pct: Optional[float] = None
    bank_margin_pct: Optional[float] = None
    wibor_pct: Optional[float] = None
    tires_included: Optional[bool] = None
    tire_buyback: Optional[bool] = None
    insurance_included: Optional[bool] = None
    replacement_car: Optional[bool] = None
    service_included: Optional[bool] = None


class SimilarBatchRequest(BaseModel):
    vehicle_ids: list[str]
    limit: int = 5
    duration_months: Optional[int] = None
    annual_mileage: Optional[int] = None
    mode: str = "rule-based"  # "rule-based" or "semantic"
    requirements: Optional[List[ScoringRequirement]] = None


class SimilarBatchItem(SimilarVehicleMatch):
    source_vehicle_id: str


class SimilarBatchResponse(BaseModel):
    results: dict[str, list[SimilarVehicleMatch]]
