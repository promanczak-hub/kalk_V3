// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { buildCalculationContext, type BaseCalculationPayload } from './payloadBuilders';

describe('buildCalculationContext', () => {
  it('should construct a valid payload with base_cost_only mode', () => {
    const basePayload: BaseCalculationPayload = {
      base_price_net: 100000,
      brand: 'Toyota',
      samar_class_id: 1,
    };

    const result = buildCalculationContext(basePayload, {
      months: 48,
      totalKm: 80000,
      calculationMode: 'base_cost_only'
    });

    expect(result).toMatchObject({
      base_price_net: 100000,
      brand: 'Toyota',
      samar_class_id: 1,
      okres_bazowy: 48,
      przebieg_bazowy: 80000,
      calculation_mode: 'base_cost_only',
      // backward compatibility check
      pricing_margin_pct: 0.001,
    });
  });

  it('should cleanly apply standard duration and mileage without mode flag', () => {
    const basePayload: BaseCalculationPayload = { base_price_net: 50000 };
    const result = buildCalculationContext(basePayload, {
      months: 24,
      totalKm: 40000
    });

    expect(result).toMatchObject({
      base_price_net: 50000,
      okres_bazowy: 24,
      przebieg_bazowy: 40000,
    });
    expect(result.calculation_mode).toBeUndefined();
  });
});
