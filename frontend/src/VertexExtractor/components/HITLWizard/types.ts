// HITL Wizard — shared TypeScript types

export type BucketId = "base" | "factory" | "zabudowa" | "agregat" | "skip";
export type PriceType = "netto" | "brutto";
export type CabinKind =
  | "podwozie"
  | "podwozie_brygadowe"
  | "furgon"
  | "furgon_brygadowy";
export type ZabudowaSotKey =
  | "SKRZYNIA"
  | "KONTENER"
  | "WYWROTKA"
  | "PLANDEKA"
  | "CHLODNIA"
  | "IZOTERMA";
export type RabatType = "kwotowo" | "procentowo";
export type RabatBasis = "netto" | "brutto";

export interface ItemDraft {
  field_id: string;
  name: string;
  // Original LLM-extracted price (numeric)
  price_value: number;
  price_type: PriceType;
  vat_rate: number; // 0.23, 0.08, 0.05, 0.0
  category: string;
  confidence: number; // 0.0-1.0
  source_section?: string; // "paid_options[3]" / "service_equipment.components[1]"
  bucket: BucketId; // current bucket assignment
  is_duplicate_candidate?: boolean;
}

export interface DiscountDraft {
  rabat_type: RabatType;
  rabat_basis: RabatBasis;
  rabat_value: number;
  discount_scope: ("base" | "factory_options" | "zabudowa" | "agregat")[];
}

export interface PreviewResponse {
  vehicle_id: string;
  composite_body_style: string | null;
  body_type: {
    body_type_id: number;
    matched_name: string;
    vehicle_class: string;
    match_method: string;
    score: number;
    utrata_wartosci: number;
  } | null;
  capex: {
    base: number;
    factory: number;
    zabudowa: number;
    agregat: number;
    total_capex: number;
  };
  discount_preview: DiscountDraft | null;
}

export interface ApplyResponse extends PreviewResponse {
  status: string;
  verification_status: string;
}

export const ZABUDOWA_PALETTE_ORDER: ZabudowaSotKey[] = [
  "KONTENER",
  "CHLODNIA",
  "IZOTERMA",
  "SKRZYNIA",
  "WYWROTKA",
  "PLANDEKA",
];

export const CABIN_PALETTE_ORDER: CabinKind[] = [
  "podwozie",
  "podwozie_brygadowe",
  "furgon",
  "furgon_brygadowy",
];

export const CABIN_LABEL: Record<CabinKind, string> = {
  podwozie: "Podwozie",
  podwozie_brygadowe: "Podwozie Brygadowe",
  furgon: "Furgon",
  furgon_brygadowy: "Furgon Brygadowy",
};

export const ZABUDOWA_LABEL: Record<ZabudowaSotKey, string> = {
  KONTENER: "Kontener",
  CHLODNIA: "Chłodnia",
  IZOTERMA: "Izoterma",
  SKRZYNIA: "Skrzynia",
  WYWROTKA: "Wywrotka",
  PLANDEKA: "Plandeka",
};

export const BUCKET_LABEL: Record<BucketId, string> = {
  base: "🚗 Cena bazowa pojazdu",
  factory: "⚙️ Opcje fabryczne",
  zabudowa: "📦 Zabudowa specjalistyczna",
  agregat: "❄️ Agregat / wyposażenie dodatkowe",
  skip: "🚫 Pomiń",
};

export const BUCKET_ORDER: BucketId[] = [
  "base",
  "factory",
  "zabudowa",
  "agregat",
  "skip",
];

// Keywords for client-side duplicate detection (mirror backend
// _DEALER_EXTRA_KEYWORDS for UI tagging — strictly informational)
export const DUPLICATE_KEYWORDS = [
  "zabudowa",
  "kontener",
  "izoterm",
  "chłodni",
  "chlodni",
  "wywrotka",
  "plandeka",
  "agregat",
  "winda",
  "hds",
];

export function confidenceColor(c: number): "red" | "amber" | "green" {
  if (c < 0.4) return "red";
  if (c < 0.7) return "amber";
  return "green";
}
