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

export interface BrochureEquipmentCategory {
  category_name: string;
  group: EquipmentGroup;
  items: string[];
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
  // Masses & dimensions
  dimensions: BrochureDimensions;
  // Equipment (3 groups, reuses generic category structure)
  equipment_categories: BrochureEquipmentCategory[];
}

const asRecord = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" ? (v as Record<string, unknown>) : {};

const str = (v: unknown): string =>
  v === null || v === undefined ? "" : String(v).trim();

// Extract horsepower from card_summary.power_hp, else parse "… 265 KM" from powertrain.
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
  // Prefer digital_twin.dimensions (the surface the UI already displays), fall back to card_summary.dimensions.
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

  // 1) Standard equipment — list[str]
  const std = (vehicle.standard_equipment || [])
    .map((s) => str(s))
    .filter((s) => s !== "");
  if (std.length > 0) {
    categories.push({ category_name: "Wyposażenie standardowe", group: "standard", items: std });
  }

  // 2) Paid options — {name, price, category}[] → names only (white-label, no prices)
  const paid = (vehicle.paid_options || [])
    .map((o) => str(o?.name))
    .filter((s) => s !== "");
  if (paid.length > 0) {
    categories.push({ category_name: "Dodatki płatne (opcje fabryczne)", group: "paid", items: paid });
  }

  // 3) Service equipment / zabudowa — card_summary.service_equipment {name, components[]}
  const service = asRecord(cardSummary.service_equipment);
  const serviceItems: string[] = [];
  const serviceName = str(service.name);
  if (serviceName) serviceItems.push(serviceName);
  const components = Array.isArray(service.components) ? service.components : [];
  for (const c of components) {
    const n = str(asRecord(c).name);
    if (n && n !== serviceName) serviceItems.push(n);
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
    dimensions: buildDimensions(synthesis),
    equipment_categories: buildEquipment(vehicle, cardSummary),
  };
}
