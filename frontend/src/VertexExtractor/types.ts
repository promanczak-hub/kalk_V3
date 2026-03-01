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

  // Brochure fields
  model_description?: string | null;
  available_powertrains?: string[] | null;
  available_trims?: string[] | null;
  starting_price?: string | null;

  synthesis_data?: Record<string, unknown> | null;
  suggested_discount_pct?: number | null;
  suggested_discount_source?: string | null;
  express_discount_match?: {
    is_matched: boolean;
    matched_discount_perc?: number;
    matching_reason?: string;
  } | null;
  created_at: string;
}
