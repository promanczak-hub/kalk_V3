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

export interface PriceValidationWarning {
  rule: string;
  message: string;
  severity: "INFO" | "WARNING" | "ERROR";
  expected?: number;
  actual?: number;
  diff_pct?: number;
}

export interface PriceValidation {
  is_valid: boolean;
  warnings: PriceValidationWarning[];
  parsed_prices?: {
    base: number | null;
    options: number | null;
    total: number | null;
  };
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
