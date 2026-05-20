import type { FleetVehicleView } from "../../types";

// ── Brochure data model (built client-side from the already-normalized vehicle row) ──
// RAW extracted values — NOT SOT-mapped. The fleet_management_view already flattens
// card_summary into top-level columns; deep fields (masses/dimensions, vin,
// service_equipment) are read from synthesis_data.{digital_twin,card_summary}.

export interface BrochureVehicleName {
  brand: string;
  model: string;
  edition: string;
  engine: string;
  body_type: string;
  horsepower: string;
}

export interface BrochureDimensions {
  length_mm?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
  wheelbase_mm?: number | null;
  curb_weight_kg?: number | null;
  gross_vehicle_weight_kg?: number | null;
  payload_kg?: number | null;
  fuel_tank_capacity_l?: number | null;
  cargo_volume_m3?: number | null;
  cargo_length_mm?: number | null;
  cargo_width_mm?: number | null;
  cargo_height_mm?: number | null;
}

export type EquipmentGroup = "standard" | "paid" | "service";

export interface BrochureEquipmentItem {
  label: string;
  price?: string;
}

export interface BrochureEquipmentCategory {
  category_name: string;
  group: EquipmentGroup;
  items: BrochureEquipmentItem[];
}

// Catalog prices only (no discount / dealer-special / monthly rate). `domain`
// flags netto vs brutto so the PDF can mark exactly what the figures mean.
export interface BrochurePrices {
  base: string | null;
  options: string | null;
  totalCatalog: string | null;
  domain: "netto" | "brutto" | null;
}

export interface BrochureData {
  vehicle_name: BrochureVehicleName;
  transmission: string;
  drive_type: string;
  // Identifiers (header)
  offer_number: string;
  configuration_code: string;
  vin: string;
  // Specs
  fuel: string;
  emissions: string;
  wheels: string;
  number_of_seats: string;
  exterior_color: string;
  engine_capacity: string;
  power_kw: string;
  // Masses & dimensions
  dimensions: BrochureDimensions;
  // Catalog prices
  prices: BrochurePrices;
  // Equipment (3 groups, reuses generic category structure)
  equipment_categories: BrochureEquipmentCategory[];
}

const asRecord = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" ? (v as Record<string, unknown>) : {};

const str = (v: unknown): string =>
  v === null || v === undefined ? "" : String(v).trim();

// Parse a price string into a number. Handles mixed formats seen in the data:
// "185 600 PLN brutto", "167 218.50 zł" (dot decimal), "1.234,56" (dot thousands,
// comma decimal), "126 200". Returns null for "Brak"/empty.
function parsePrice(s: string): number | null {
  if (!s) return null;
  if (s.toLowerCase().includes("brak")) return null;
  let t = s.replace(/[^\d.,]/g, ""); // drop spaces, currency words
  if (!t) return null;
  const hasComma = t.includes(",");
  const hasDot = t.includes(".");
  if (hasComma && hasDot) {
    t = t.replace(/\./g, "").replace(",", "."); // dot=thousands, comma=decimal
  } else if (hasComma) {
    t = t.replace(",", ".");
  } else if (hasDot) {
    const m = t.match(/\.(\d+)$/);
    if (m && m[1].length === 3) t = t.replace(/\./g, ""); // ".200" → thousands
  }
  const n = parseFloat(t);
  return isNaN(n) ? null : n;
}

// Format a number as Polish currency "126 200 zł" (manual space thousands separator,
// no locale — avoids non-breaking spaces that break @react-pdf text + ESLint).
function formatZl(n: number): string {
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " zł";
}

function detectDomain(cardSummary: Record<string, unknown>, blob: string): "netto" | "brutto" | null {
  const pd = str(cardSummary.price_domain).toLowerCase();
  if (pd.includes("netto")) return "netto";
  if (pd.includes("brutto")) return "brutto";
  const b = blob.toLowerCase();
  if (b.includes("netto")) return "netto";
  if (b.includes("brutto")) return "brutto";
  return null;
}

function buildPrices(vehicle: FleetVehicleView, cardSummary: Record<string, unknown>): BrochurePrices {
  const baseRaw = str(vehicle.base_price);
  const optRaw = str(vehicle.options_price);
  const baseN = parsePrice(baseRaw);
  const optN = parsePrice(optRaw);
  return {
    base: baseN != null ? formatZl(baseN) : null,
    options: optN != null ? formatZl(optN) : null,
    totalCatalog: baseN != null ? formatZl(baseN + (optN ?? 0)) : null,
    domain: detectDomain(cardSummary, `${baseRaw} ${optRaw}`),
  };
}

// Resolve a catalog amount from a paid-option / service object (number fields first, then strings).
function amountOf(obj: Record<string, unknown>): string | undefined {
  const g = obj.gross_amount;
  if (typeof g === "number" && g > 0) return formatZl(g);
  const pg = parsePrice(str(obj.price_gross));
  if (pg != null && pg > 0) return formatZl(pg);
  const raw = parsePrice(str(obj.price));
  if (raw != null) return formatZl(raw);
  const n = obj.net_amount;
  if (typeof n === "number" && n > 0) return formatZl(n);
  const pn = parsePrice(str(obj.price_net));
  if (pn != null && pn > 0) return formatZl(pn);
  return undefined;
}

function resolveHorsepower(cardSummary: Record<string, unknown>, powertrain: string): string {
  const hp = cardSummary.power_hp;
  if (typeof hp === "number" && hp > 0) return String(hp);
  if (typeof hp === "string" && hp.trim()) return hp.trim();
  const m = powertrain.match(/(\d{2,4})\s*(?:KM|HP|PS)/i);
  return m ? m[1] : "";
}

function buildDimensions(synthesis: Record<string, unknown>): BrochureDimensions {
  const digitalTwin = asRecord(synthesis.digital_twin);
  const cardSummary = asRecord(synthesis.card_summary);
  const dt = asRecord(digitalTwin.dimensions);
  const cs = asRecord(cardSummary.dimensions);
  const pick = (k: string): number | null => {
    const a = dt[k];
    if (typeof a === "number") return a;
    const b = cs[k];
    if (typeof b === "number") return b;
    return null;
  };
  return {
    length_mm: pick("length_mm"),
    width_mm: pick("width_mm"),
    height_mm: pick("height_mm"),
    wheelbase_mm: pick("wheelbase_mm"),
    curb_weight_kg: pick("curb_weight_kg"),
    gross_vehicle_weight_kg: pick("gross_vehicle_weight_kg"),
    payload_kg: pick("payload_kg"),
    fuel_tank_capacity_l: pick("fuel_tank_capacity_l"),
    cargo_volume_m3: pick("cargo_volume_m3"),
    cargo_length_mm: pick("cargo_length_mm"),
    cargo_width_mm: pick("cargo_width_mm"),
    cargo_height_mm: pick("cargo_height_mm"),
  };
}

function buildEquipment(
  vehicle: FleetVehicleView,
  cardSummary: Record<string, unknown>,
): BrochureEquipmentCategory[] {
  const categories: BrochureEquipmentCategory[] = [];

  // 1) Standard equipment — list[str], no prices.
  const std = (vehicle.standard_equipment || [])
    .map((s) => str(s))
    .filter((s) => s !== "")
    .map((label) => ({ label }));
  if (std.length > 0) {
    categories.push({ category_name: "Wyposażenie standardowe", group: "standard", items: std });
  }

  const toItem = (rec: Record<string, unknown>): BrochureEquipmentItem | null => {
    const label = str(rec.name);
    if (!label) return null;
    const price = amountOf(rec);
    return price ? { label, price } : { label };
  };

  // 2) Paid options — {name, price}[] with catalog price per item.
  const paid = (vehicle.paid_options || [])
    .map((o) => toItem(asRecord(o)))
    .filter((x): x is BrochureEquipmentItem => x !== null);
  if (paid.length > 0) {
    categories.push({ category_name: "Wyposażenie opcjonalne i usługi", group: "paid", items: paid });
  }

  // 3) Service equipment / zabudowa — components (name + catalog price), else the single entry.
  const service = asRecord(cardSummary.service_equipment);
  const components = Array.isArray(service.components) ? service.components : [];
  let serviceItems: BrochureEquipmentItem[] = [];
  if (components.length > 0) {
    serviceItems = components
      .map((c) => toItem(asRecord(c)))
      .filter((x): x is BrochureEquipmentItem => x !== null);
  } else {
    const item = toItem(service);
    if (item) serviceItems = [item];
  }
  if (serviceItems.length > 0) {
    categories.push({
      category_name: "Wyposażenie serwisowe / zabudowa",
      group: "service",
      items: serviceItems,
    });
  }

  return categories;
}

export function buildBrochureData(vehicle: FleetVehicleView): BrochureData {
  const synthesis = asRecord(vehicle.synthesis_data);
  const cardSummary = asRecord(synthesis.card_summary);
  const powertrain = str(vehicle.powertrain);
  const powerKw = cardSummary.power_kw;

  return {
    vehicle_name: {
      brand: str(vehicle.brand),
      model: str(vehicle.model),
      edition: str(vehicle.trim_level),
      engine: powertrain,
      body_type: str(vehicle.body_style),
      horsepower: resolveHorsepower(cardSummary, powertrain),
    },
    transmission: str(vehicle.transmission),
    drive_type: str(vehicle.drive_type) || str(cardSummary.drive_type),
    offer_number: str(vehicle.offer_number),
    configuration_code: str(vehicle.configuration_code),
    vin: str(cardSummary.vin),
    fuel: str(vehicle.fuel),
    emissions: str(vehicle.emissions),
    wheels: str(vehicle.wheels),
    number_of_seats: vehicle.number_of_seats ? String(vehicle.number_of_seats) : "",
    exterior_color: str(vehicle.exterior_color),
    engine_capacity: str(cardSummary.engine_capacity),
    power_kw: typeof powerKw === "number" && powerKw > 0 ? String(powerKw) : str(powerKw),
    dimensions: buildDimensions(synthesis),
    prices: buildPrices(vehicle, cardSummary),
    equipment_categories: buildEquipment(vehicle, cardSummary),
  };
}
