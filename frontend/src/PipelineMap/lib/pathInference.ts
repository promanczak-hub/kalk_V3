/**
 * Heurystycznie wnioskuje ścieżkę pipeline'u użytą do wytworzenia
 * konkretnej kalkulacji — na podstawie `synthesis_data.calculator_setup`.
 *
 * To NIE jest realny trace wykonania (ten by wymagał kolumny pipeline_trace
 * JSONB w DB i tracking middleware — przesunięte do v2). Zamiast tego
 * stosujemy deterministyczne reguły:
 *
 * - Jeśli kalkulacja istnieje → cały pipeline PDF→synthesis + 12 stagów LTR
 * - Toggle off → stage przyciemniony (disabled)
 * - service_cost_type=nonASO → stage Serwis ma variant-nonASO
 * - active_discount_pct → highlight endpointu discount-override
 */

import type { FleetVehicleView } from "../../VertexExtractor/types";
import type { HighlightMap, HighlightMode, TopologyResponse } from "../types";

interface CalculatorSetup {
  saved_at?: string;
  service_cost_type?: "ASO" | "nonASO" | string;
  toggles?: {
    include_servicing?: boolean;
    include_tires?: boolean;
    replacement_car?: boolean;
    express_pays_insurance?: boolean;
    gps?: boolean;
    hook?: boolean;
    registration?: boolean;
    sales_prep?: boolean;
  };
  discount?: {
    active_discount_pct?: number | null;
    active_final_price?: number | null;
  };
}

function getSetup(v: FleetVehicleView): CalculatorSetup | null {
  const syn = v.synthesis_data as Record<string, unknown> | null | undefined;
  if (!syn) return null;
  const setup = syn["calculator_setup"];
  if (!setup || typeof setup !== "object") return null;
  return setup as CalculatorSetup;
}

/**
 * Zwraca HighlightMap dla danej kalkulacji.
 * Pusta mapa = brak aktywnej kalkulacji = wszystkie nody w "normal" (pełny kolor).
 */
export function inferHighlight(
  vehicle: FleetVehicleView | null,
  topology: TopologyResponse,
): HighlightMap {
  const map = new Map<string, HighlightMode>();
  if (!vehicle) return map;

  const setup = getSetup(vehicle);
  const hasCalc = setup !== null;
  if (!hasCalc) return map;

  // Pomocniczy set wszystkich istniejących node id (do walidacji że highlight wskazuje istniejące)
  const existing = new Set(topology.nodes.map((n) => n.id));

  function mark(id: string, mode: HighlightMode = "highlighted"): void {
    if (existing.has(id)) {
      // Wariant/disabled wygrywa z plain highlighted
      const prev = map.get(id);
      if (prev === "variant-nonASO" || prev === "disabled") return;
      map.set(id, mode);
    }
  }

  // 1) Pipeline PDF → synthesis (zawsze gdy istnieje calculator_setup)
  mark("route:POST:/api/extract/async");
  mark("task:process_document_task_from_storage");
  mark("task:process_document_task");
  mark("phase:0:router");
  mark("phase:0:multi_vehicle");
  mark("phase:1:twins");
  mark("phase:2:mapping");
  mark("db:vehicle_synthesis");

  // 2) 12 stagów LTR + ich tabele DB
  for (let i = 1; i <= 12; i++) {
    mark(`stage:ltr:${i}`);
  }
  mark("db:ltr_kalkulacje");
  mark("db:body_types");
  mark("db:samar_rv");
  mark("db:control_center");

  // 3) Endpoint kalkulacji (najpewniejszy kandydat)
  mark("route:POST:/api/kalkulacje");
  mark("route:POST:/api/calculate-matrix");

  // 4) Warianty z toggles
  const t = setup?.toggles;
  if (t?.include_servicing === false) mark("stage:ltr:4", "disabled");
  if (t?.include_tires === false) mark("stage:ltr:1", "disabled");
  if (t?.replacement_car === false) mark("stage:ltr:3", "disabled");
  if (t?.express_pays_insurance === false) mark("stage:ltr:8", "disabled");

  // 5) Wariant nonASO dla serwisu
  if (setup?.service_cost_type === "nonASO" && t?.include_servicing !== false) {
    mark("stage:ltr:4", "variant-nonASO");
  }

  // 6) Discount override
  if (setup?.discount?.active_discount_pct != null) {
    mark("route:POST:/api/extract/discount-override/{vehicle_id}");
  }

  return map;
}
