/**
 * Tests for `buildCalculationContext` — the FE→BE payload boundary.
 *
 * Pre-refactor 2026-05-19 the file had `@ts-nocheck` on top; fixed by
 * tightening types in the test itself, not the source.
 */
import { describe, expect, it } from "vitest";
import {
  buildCalculationContext,
  type BaseCalculationPayload,
} from "./payloadBuilders";

describe("buildCalculationContext", () => {
  it("constructs a valid payload with base_cost_only mode", () => {
    const basePayload: BaseCalculationPayload = {
      base_price_net: 100000,
      brand: "Toyota",
      samar_class_id: 1,
    };

    const result = buildCalculationContext(basePayload, {
      months: 48,
      totalKm: 80000,
      calculationMode: "base_cost_only",
    });

    expect(result).toMatchObject({
      base_price_net: 100000,
      brand: "Toyota",
      samar_class_id: 1,
      okres_bazowy: 48,
      przebieg_bazowy: 80000,
      calculation_mode: "base_cost_only",
      // Backward compat: legacy pricing_margin_pct must still be present.
      pricing_margin_pct: 0.001,
    });
  });

  it("applies duration + mileage when no mode flag is set", () => {
    const basePayload: BaseCalculationPayload = { base_price_net: 50000 };
    const result = buildCalculationContext(basePayload, {
      months: 24,
      totalKm: 40000,
    });

    expect(result).toMatchObject({
      base_price_net: 50000,
      okres_bazowy: 24,
      przebieg_bazowy: 40000,
    });
    expect(result.calculation_mode).toBeUndefined();
  });

  it("preserves pricingMarginPct override outside base_cost_only mode", () => {
    const basePayload: BaseCalculationPayload = { base_price_net: 70000 };
    const result = buildCalculationContext(basePayload, {
      months: 36,
      totalKm: 60000,
      pricingMarginPct: 12.5,
    });

    expect(result.pricing_margin_pct).toBe(12.5);
    expect(result.calculation_mode).toBeUndefined();
  });

  it("keeps existing keys from basePayload through the spread", () => {
    // Stress the `[key: string]: unknown` extensibility — fields not in the
    // interface must still survive the spread (FE forwards lots of derived
    // setup state to BE that's not in the strict Pydantic schema).
    const basePayload: BaseCalculationPayload = {
      base_price_net: 90000,
      brand: "Skoda",
      model: "Octavia",
      // Extra field via index signature
      custom_marker: "preserve-me",
    };
    const result = buildCalculationContext(basePayload, {
      months: 60,
      totalKm: 120000,
    });

    expect(result.custom_marker).toBe("preserve-me");
    expect(result.brand).toBe("Skoda");
    expect(result.model).toBe("Octavia");
  });

  it("does not mutate the input basePayload", () => {
    const basePayload: BaseCalculationPayload = {
      base_price_net: 55000,
      brand: "Audi",
    };
    const snapshot = { ...basePayload };
    buildCalculationContext(basePayload, { months: 48, totalKm: 80000 });
    expect(basePayload).toEqual(snapshot);
  });
});
