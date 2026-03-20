export interface BaseCalculationPayload {
  samar_class_id?: number | null;
  samar_engine_id?: number | null;
  body_type?: string | null;
  brand?: string | null;
  model?: string | null;
  base_price_net: number;
  rocznik?: number;
  
  global_settings?: Record<string, unknown>;
  
  [key: string]: unknown; // Allow flexibility for now
}

export interface CalculationContextParams {
  months: number;
  totalKm: number;
  pricingMarginPct?: number; // legacy hack
  calculationMode?: 'standard' | 'base_cost_only'; // new parameter for TICK-12
}

/**
 * Builds the payload required for the calculation matrix endpoint.
 * This ensures that critical numeric values are correctly typed and required fields are present.
 */
export function buildCalculationContext(
  basePayload: BaseCalculationPayload,
  params: CalculationContextParams
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    ...basePayload,
    okres_bazowy: params.months,
    przebieg_bazowy: params.totalKm,
  };

  // Legacy fallback (TICK-12 compatibility) vs modern calculation_mode
  if (params.calculationMode === 'base_cost_only') {
    payload.calculation_mode = 'base_cost_only';
    payload.pricing_margin_pct = params.pricingMarginPct ?? 0.001; 
  } else if (params.pricingMarginPct !== undefined) {
    payload.pricing_margin_pct = params.pricingMarginPct;
  }

  return payload;
}
