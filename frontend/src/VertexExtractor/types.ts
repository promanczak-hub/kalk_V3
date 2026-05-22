export type DocumentStatus =
  | "idle"
  | "uploading"
  | "processing"
  | "completed"
  | "error";

export interface UploadedDocument {
  id: string;
  name: string;
  size: number;
  type: "pdf" | "excel";
  status: DocumentStatus;
  jsonResult?: string;
  originalFile?: File;
  fileHash?: string;
}

export interface FleetVehicleView {
  id: string;
  verification_status: string | null;
  brand: string | null;
  model: string | null;
  offer_number: string | null;
  configuration_code: string | null;
  raw_pdf_url: string | null;
  engine_marketing_name?: string | null;
  powertrain: string | null;
  body_style: string | null;
  document_category: string | null;
  vehicle_class: string | null;
  trim_level: string | null;
  fuel: string | null;
  transmission: string | null;
  base_price: string | null;
  options_price: string | null;
  final_price_pln: string | null;
  wheels: string | null;
  emissions: string | null;
  exterior_color: string | null;
  drive_type: string | null;
  number_of_seats: number | null;
  is_metalic_paint: boolean | null;
  notes: string | null;
  standard_equipment: string[] | null;
  paid_options: { name: string; price: string; category?: string }[] | null;
  // Service interval
  service_interval_km: number | null;
  service_interval_months: number | null;

  // Brochure fields
  model_description?: string | null;
  available_powertrains?: string[] | null;
  available_trims?: string[] | null;
  starting_price?: string | null;

  synthesis_data?: Record<string, unknown> | null;
  koszt_dzienny_min?: number | null;
  suggested_discount_pct?: number | null;
  suggested_discount_confidence?: number | null;
  suggested_discount_source?: string | null;
  express_discount_match?: {
    is_matched: boolean;
    matched_discount_perc?: number;
    matching_reason?: string;
  } | null;
  created_at: string;

  // Price validation flags (injected by pipeline_price_validator.py)
  price_validation?: PriceValidation | null;

  [key: string]: any; // Allow dynamic raw data access
}

export interface CatalogFeature {
  id: string;
  feature_key: string;
  display_name: string;
  feature_type: "boolean" | "bool" | "numeric" | "enum" | "string" | string;
  metadata?: any;
  applicable_body_types?: string[];
}

export interface CatalogCategory {
  id: string;
  display_name: string;
  features: CatalogFeature[];
}

export interface SearchFilter {
  feature_key: string;
  display_name?: string;
  value_bool?: boolean;
  value_num_min?: number;
  value_num_max?: number;
  value_text?: string;
}

export interface SearchResult {
  vehicle_id: string;
  brand: string;
  model: string;
  score: number;
  matched_feature_keys?: string[];
  missing_feature_keys?: string[];
  matched_features?: number;
  total_filters?: number;
  match_score?: number;
  source_vehicle_id?: string;
  price_netto?: number | null;
  score_features_pct?: number | null;
  score_semantic?: number | null;
  [key: string]: any;
}

export const CURATED_SHARED: string[] = ["klimatyzacja", "czujniki", "kamera", "tempomat"];
export const CURATED_PASSENGER: string[] = ["podgrzewane_fotele", "skora", "szyberdach", "isofix"];
export const CURATED_COMMERCIAL: string[] = ["drzwi_przesuwne", "sklejka", "hak"];

export function getSliderBounds(featName: string): { min: number; max: number } {
  if (featName.toLowerCase().includes("moc")) return { min: 50, max: 500 };
  if (featName.toLowerCase().includes("pojemność")) return { min: 900, max: 5000 };
  return { min: 0, max: 10000 };
}

export interface PriceValidationWarning {
  rule: string;
  message: string;
  severity: "INFO" | "WARNING" | "ERROR";
  expected?: number;
  actual?: number;
  diff_pct?: number;
}

export interface PriceValidationSummary {
  verdict: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  details: string;
  suggestions: string[];
}

export interface PriceValidation {
  is_valid: boolean;
  warnings: PriceValidationWarning[];
  parsed_prices?: {
    base: number | null;
    options: number | null;
    total: number | null;
  };
  summary?: PriceValidationSummary;
}

export interface DeducedOption {
  field_id?: string;
  name: string;
  net: number;
  gross: number;
  bucket: "katalogowa" | "fabryczna" | "serwisowa";
  discountable: boolean;
}

export interface PriceDeduction {
  source_domain: "netto" | "brutto" | "unknown";
  base_net: number;
  base_gross: number;
  discountable_options_net: number;
  discountable_options_gross: number;
  non_discountable_options_net: number;
  non_discountable_options_gross: number;
  service_net: number;
  service_gross: number;
  total_net: number;
  total_gross: number;
  rabat_pln: number;
  vat_rate: number;
  options: DeducedOption[];
  deduced_fields: string[];
  reasoning: string;
  confidence: number;
}

// ── Multi-hypothesis price reconciliation (4 net/brutto paths + LLM judge) ──

export interface ReconPath {
  source_domain: "netto" | "brutto";
  final_domain: "netto" | "brutto";
  base_net: number;
  base_gross: number;
  options_net: number;
  options_gross: number;
  service_net: number;
  service_gross: number;
  rabat_net: number;
  rabat_gross: number;
  catalog_net: number;
  catalog_gross: number;
  total_net: number;
  total_gross: number;
  residual_pln: number;
  penalties: number;
  score: number;
}

export interface ReconJudge {
  agrees_with_winner?: boolean;
  chosen_source_domain?: string;
  reasoning?: string;
  confidence?: number;
}

export interface PriceReconciliation {
  verdict: "ok" | "ambiguous" | "unreconcilable";
  source_domain: "netto" | "brutto";
  best: ReconPath;
  all_paths: ReconPath[];
  warning?: { rule: string; severity: string; message: string; field_path?: string } | null;
  judge?: ReconJudge | null;
}

export type DiscountExtractionMethod =
  | "explicit_amount"
  | "explicit_percentage"
  | "computed_from_total"
  | "none";

export interface DiscountBreakdown {
  explicit_rabat_pln: number | null;
  explicit_rabat_pct: number | null;
  discountable_base_net: number | null;
  non_discountable_total_net: number | null;
  computed_pct: number | null;
  extraction_method: DiscountExtractionMethod;
  confidence: number;
  audit_notes: string[];
}
export interface ModificationEffect {
  override_samar_class?: string | null;
  override_homologation?: string | null;
  adds_weight_kg?: number | null;
  is_financial_only?: boolean;
}

export interface ServiceOptionPayload {
  name: string;
  category: string;
  price_net?: number | null;
  effects?: ModificationEffect | null;
}

export interface HomologationResponse {
  new_samar_category: string | null;
  new_vehicle_type: string | null;
  payload_loss_kg: number;
  dynamic_payload_kg: number | null;
  homologation_alerts: string[];
  samar_override_applied: boolean;
}
