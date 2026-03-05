import { useMemo } from "react";
import type { FleetVehicleView } from "../types";
import { parsePriceToNumber } from "../components/VehicleTableParts/PriceDualFormat";

export interface DiscountAlert {
  type: "cross_card" | "db_higher";
  siblingVehicleId: string;
  siblingOfferNumber: string | null;
  siblingDiscountPct: number;
  currentDiscountPct: number;
  deltaPp: number;
}

function normalizeKey(brand: string | null, model: string | null): string {
  const b = (brand ?? "").trim().toLowerCase();
  const m = (model ?? "").trim().toLowerCase();
  if (!b || !m) return "";
  return `${b}__${m}`;
}

function computeEffectiveDiscount(vehicle: FleetVehicleView): number {
  const basePrice = parsePriceToNumber(vehicle.base_price);
  const optionsPrice = parsePriceToNumber(vehicle.options_price);
  const totalCatalog = basePrice + optionsPrice;
  const offerFinalPrice = parsePriceToNumber(vehicle.final_price_pln);

  const hasOfferFinal = Boolean(
    vehicle.final_price_pln &&
      vehicle.final_price_pln !== "Brak" &&
      vehicle.final_price_pln !== vehicle.base_price,
  );

  const isDealerOffer = Boolean(
    hasOfferFinal &&
      offerFinalPrice > 0 &&
      offerFinalPrice < totalCatalog - 1.0,
  );

  const cardSummary = vehicle.synthesis_data?.card_summary as
    | Record<string, unknown>
    | undefined;
  const parsedOfferDiscountPct = cardSummary?.offer_discount_pct;

  const offerDiscountPct = parsedOfferDiscountPct
    ? Number(parsedOfferDiscountPct)
    : isDealerOffer && totalCatalog > 0
      ? Number(
          (((totalCatalog - offerFinalPrice) / totalCatalog) * 100).toFixed(1),
        )
      : 0;

  const suggestedPct = vehicle.suggested_discount_pct ?? 0;

  return Math.max(offerDiscountPct, suggestedPct);
}

/**
 * Computes cross-card discount alerts for vehicles sharing the same brand+model.
 * Returns a Map keyed by vehicle.id → DiscountAlert[].
 */
export function useDiscountAlerts(
  vehicles: FleetVehicleView[],
): Map<string, DiscountAlert[]> {
  return useMemo(() => {
    const alertsMap = new Map<string, DiscountAlert[]>();

    // 1. Group by brand+model
    const groups = new Map<string, FleetVehicleView[]>();
    for (const v of vehicles) {
      if (v.verification_status === "cancelled") continue;
      const key = normalizeKey(v.brand, v.model);
      if (!key) continue;

      const existing = groups.get(key);
      if (existing) {
        existing.push(v);
      } else {
        groups.set(key, [v]);
      }
    }

    // 2. For each group with ≥2 vehicles, compare discounts
    for (const group of groups.values()) {
      if (group.length < 2) continue;

      const discounts = group.map((v) => ({
        vehicle: v,
        effectivePct: computeEffectiveDiscount(v),
      }));

      const bestInGroup = Math.max(...discounts.map((d) => d.effectivePct));

      for (const entry of discounts) {
        if (entry.effectivePct >= bestInGroup) continue;

        const delta = Number(
          (bestInGroup - entry.effectivePct).toFixed(1),
        );
        if (delta < 0.1) continue;

        // Find the sibling(s) that have the best discount
        const bestSibling = discounts.find(
          (d) =>
            d.vehicle.id !== entry.vehicle.id &&
            d.effectivePct === bestInGroup,
        );

        if (!bestSibling) continue;

        const alert: DiscountAlert = {
          type: "cross_card",
          siblingVehicleId: bestSibling.vehicle.id,
          siblingOfferNumber: bestSibling.vehicle.offer_number,
          siblingDiscountPct: bestSibling.effectivePct,
          currentDiscountPct: entry.effectivePct,
          deltaPp: delta,
        };

        const existing = alertsMap.get(entry.vehicle.id);
        if (existing) {
          existing.push(alert);
        } else {
          alertsMap.set(entry.vehicle.id, [alert]);
        }
      }
    }

    return alertsMap;
  }, [vehicles]);
}
