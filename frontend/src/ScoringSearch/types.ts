export interface FilterItem {
  value: string;
  count: number;
}

export interface EnumFilter {
  key: string;
  name: string;
  type: 'enum';
  parent?: string | null;
  level?: number;
  primary?: boolean;
  items: FilterItem[];
}

export interface FacetGroup {
  group_name: string;
  filters: EnumFilter[];
}

export interface RangeFilter {
  feature_key: string;
  feature_name: string;
  group_name: string;
  parent_feature_key?: string | null;
  facet_level?: number;
  is_primary_facet?: boolean;
  min_val: number;
  max_val: number;
}

export interface BooleanFilter {
  feature_key: string;
  feature_name: string;
  group_name: string;
  parent_feature_key?: string | null;
  facet_level?: number;
  is_primary_facet?: boolean;
  cnt: number;
}

export interface AvailableFiltersResponse {
  filters_provided: boolean;
  facet_groups: FacetGroup[];
  range_filters: RangeFilter[];
  boolean_filters: BooleanFilter[];
}

export interface SamarClass {
  id: number;
  name: string;
}

export interface BodyType {
  name: string;
  count: number;
}

export interface InitialDataResponse {
  brands: string[];
  models: string[];
  brand_model_map: Record<string, string[]>;
  brand_counts: Record<string, number>;
  trim_level_map: Record<string, string[]>;
  samar_classes: SamarClass[];
  body_types: BodyType[];
}

export interface OptionItem {
  name: string;
  count: number;
}

export interface TrimsAndOptionsResponse {
  trim_levels: OptionItem[];
  standard_options: OptionItem[];
  paid_options: OptionItem[];
}

// User selections
export type RequirementLevel = 'MUST_HAVE' | 'NICE_TO_HAVE';
export type Operator = 'eq' | 'gte' | 'lte' | 'in';

export interface SelectedFeature {
  feature_key: string;
  operator: Operator;
  value: string | number | boolean;
  requirement: RequirementLevel;
  weight?: number;
}

export interface SearchContext {
  brands: string[];
  models: string[];
  trims: string[];
  samarClassIds: number[];
  bodyTypes: string[];
  fuelTypes: string[];
  transmissions: string[];
  driveTypes: string[];
  useMatrixFilters: boolean;
  monthly_budget?: number;
  duration_months_range: [number, number];
  total_mileage_range: [number, number];
  exact_mode: boolean;
  exact_duration_months: number;
  exact_total_mileage: number;
  margin_pct?: number;
  semanticQuery?: string;
}

export interface OptionLineItem {
  name: string;
  price_net?: number | null;
  price_gross?: number | null;
  category?: string | null;
}

export interface ScoredVehicle {
  vehicle_id: string;
  brand: string;
  model: string;
  score: number;
  match_pct?: number;
  monthly_price_net?: number;
  duration_months?: number;
  annual_mileage?: number;
  version?: string;
  fuel?: string;
  power_hp?: number;
  transmission?: string;
  body_style?: string;
  drive_type?: string;
  trim_level?: string;
  configuration_code?: string;
  offer_number?: string;
  base_price_net?: number;
  base_price_gross?: number;
  total_price_net?: number;
  total_price_gross?: number;
  options_price_net?: number;
  options_price_gross?: number;
  factory_options_price_net?: number;
  factory_options_price_gross?: number;
  service_options_price_net?: number;
  service_options_price_gross?: number;
  factory_options?: OptionLineItem[];
  service_options?: OptionLineItem[];
  engine_capacity?: string;
  engine_designation?: string;
  extraction_date?: string;
  match_score_pct?: number;
  matched_features?: string[];
  missing_features?: string[];
  best_monthly_price?: number;
  applied_margin_pct?: number;
  has_ltr_cache?: boolean;
  applied_discount_pct?: number;
  service_cost_type?: string;
  tire_class?: string;
  vehicle_class?: string;
  // User-pinned calculations (multi-select). Empty list → render as one default card.
  selected_kalkulacja_ids?: string[];
}

