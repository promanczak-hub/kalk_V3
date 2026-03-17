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

export interface InitialDataResponse {
  brands: string[];
  models: string[];
  brand_model_map: Record<string, string[]>;
  brand_counts: Record<string, number>;
  samar_classes: SamarClass[];
}

// User selections
export type RequirementLevel = 'MUST_HAVE' | 'NICE_TO_HAVE';
export type Operator = 'eq' | 'gte' | 'lte' | 'in';

export interface SelectedFeature {
  feature_key: string;
  operator: Operator;
  value: any;
  requirement: RequirementLevel;
  weight?: number;
}

export interface SearchContext {
  brands: string[];
  models: string[];
  samarClassIds: number[];
  monthly_budget?: number;
  duration_months_range: [number, number];
  annual_mileage_range: [number, number];
  margin_pct?: number;
}
