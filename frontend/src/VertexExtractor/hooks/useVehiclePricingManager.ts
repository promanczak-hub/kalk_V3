import { useState } from "react";
import type { FleetVehicleView } from "../types";
import { parsePriceToNumber } from "../components/VehicleTableParts/PriceDualFormat";

interface UseVehiclePricingProps {
  vehicle: FleetVehicleView;
  catalogBasePriceNet: number;
  customFactoryOptions: { price_net: number; no_discount: boolean }[];
  customServiceOptions: { price_net: number }[];
}

export function useVehiclePricingManager({
  vehicle,
  catalogBasePriceNet,
  customFactoryOptions,
  customServiceOptions,
}: UseVehiclePricingProps) {
  const [discountMode, setDiscountMode] = useState<"offer" | "suggested" | "custom">(() => {
    const cs = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
    const offerPct = Number(cs?.offer_discount_pct ?? 0);
    const suggestedPct = Number(vehicle.suggested_discount_pct ?? 0);

    if (Number.isFinite(offerPct) && offerPct > 0) return "offer";
    if (Number.isFinite(suggestedPct) && suggestedPct > 0) return "suggested";
    return "offer";
  });
  const [customDiscountPctRaw, setCustomDiscountPctRaw] = useState<string | number>("");

  const customDiscountPct = Number(customDiscountPctRaw) || 0;

  const cardSummary = vehicle.synthesis_data?.card_summary as Record<string, unknown> | undefined;
  const isDomainNetto = cardSummary?.price_domain === "netto" || (typeof cardSummary?.price_domain === 'string' && cardSummary.price_domain.toLowerCase().includes("netto"));
  const isGlobalNetto = vehicle.base_price?.toLowerCase().includes("netto") || isDomainNetto;

  // AI-extracted raw string for comparison display
  const aiExtractedBasePrice = vehicle.base_price || null;
  const AI_PRICE_ALERT_THRESHOLD_PLN = 10;
  const aiBasePriceRaw = parsePriceToNumber(aiExtractedBasePrice || "0");
  const aiBasePriceNet = isGlobalNetto
    ? aiBasePriceRaw
    : Math.round((aiBasePriceRaw / 1.23) * 100) / 100;
  const aiBasePriceDeltaPln = Math.abs(catalogBasePriceNet - aiBasePriceNet);
  const requireManualPriceReview = Boolean(
    aiExtractedBasePrice && aiBasePriceNet > 0 && aiBasePriceDeltaPln > AI_PRICE_ALERT_THRESHOLD_PLN
  );
  const calculationBlockReason = requireManualPriceReview
    ? `Różnica ceny bazowej względem AI wynosi ${aiBasePriceDeltaPln.toFixed(2)} PLN (limit ${AI_PRICE_ALERT_THRESHOLD_PLN} PLN). Zweryfikuj ręcznie i skoryguj cenę.`
    : null;

  // ── Dynamic option splits (must come BEFORE totalCatalogPriceNet) ──
  const factoryOptionsPriceTotal = customFactoryOptions.reduce((acc, curr) => acc + curr.price_net, 0);
  const customServiceOptionsPriceTotal = customServiceOptions.reduce((acc, curr) => acc + curr.price_net, 0);

  const dynamicTotalOptionsPrice = factoryOptionsPriceTotal + customServiceOptionsPriceTotal;

  // Split factory options into discountable / non-discountable (always Netto)
  const discountableOptionsTotal = customFactoryOptions
    .filter(opt => !opt.no_discount)
    .reduce((acc, curr) => acc + curr.price_net, 0);
  const nonDiscountableOptionsTotal = customFactoryOptions
    .filter(opt => opt.no_discount)
    .reduce((acc, curr) => acc + curr.price_net, 0);

  // totalCatalogPriceNet = base + ALL factory options
  const totalCatalogPriceNet = catalogBasePriceNet + factoryOptionsPriceTotal;

  // discountableBaseNet = base + discountable factory options
  const discountableBaseNet = catalogBasePriceNet + discountableOptionsTotal;

  const offerFinalPriceRaw = parsePriceToNumber(vehicle.final_price_pln);
  const offerFinalPriceNet = isGlobalNetto ? offerFinalPriceRaw : offerFinalPriceRaw / 1.23;

  const hasOfferFinalPrice = Boolean(
    vehicle.final_price_pln &&
    vehicle.final_price_pln !== "Brak" &&
    vehicle.final_price_pln !== vehicle.base_price
  );
  
  const isDealerOffer = Boolean(
    hasOfferFinalPrice && offerFinalPriceNet > 0 && offerFinalPriceNet < totalCatalogPriceNet - 1.0
  );
  
  const parsedOfferDiscountPctStr = cardSummary?.offer_discount_pct;
  const parsedOfferDiscountPlnStr = cardSummary?.offer_discount_pln;
  
  const parsedOfferDiscountPct = parsedOfferDiscountPctStr ? Number(parsedOfferDiscountPctStr) : 0;
  const parsedOfferDiscountPln = parsedOfferDiscountPlnStr
    ? Number(String(parsedOfferDiscountPlnStr).replace(/[^0-9.,]/g, "").replace(",", "."))
    : 0;

  const hasValidOfferDiscountPct = Boolean(parsedOfferDiscountPct > 0);
  const hasValidOfferDiscountPln = Boolean(parsedOfferDiscountPln > 0 && discountableBaseNet > 0);
  
  const hasValidOfferDiscount = hasValidOfferDiscountPct || hasValidOfferDiscountPln;
  const isDealerOfferExtended = isDealerOffer || hasValidOfferDiscount;

  const offerDiscountPercentage = hasValidOfferDiscountPct
    ? parsedOfferDiscountPct
    : hasValidOfferDiscountPln
      ? Number(((parsedOfferDiscountPln / discountableBaseNet) * 100).toFixed(2))
      : isDealerOffer && totalCatalogPriceNet > 0
        ? Number((((totalCatalogPriceNet - offerFinalPriceNet) / totalCatalogPriceNet) * 100).toFixed(1))
        : 0;

  const suggestedDiscountPct = vehicle.suggested_discount_pct || 0;
  const suggestedDiscountConfidence = vehicle.suggested_discount_confidence || 0;

  let activeDiscountPct = 0;
  let activeFinalPriceNet = totalCatalogPriceNet + customServiceOptionsPriceTotal;

  if (discountMode === "offer" && isDealerOfferExtended) {
    activeDiscountPct = offerDiscountPercentage;
    if (parsedOfferDiscountPct && !hasOfferFinalPrice) {
      activeFinalPriceNet = 
        discountableBaseNet * (1 - offerDiscountPercentage / 100)
        + nonDiscountableOptionsTotal
        + customServiceOptionsPriceTotal;
    } else {
      activeFinalPriceNet = offerFinalPriceNet;
    }
  } else if (discountMode === "suggested") {
    activeDiscountPct = suggestedDiscountPct;
    activeFinalPriceNet =
      discountableBaseNet * (1 - suggestedDiscountPct / 100)
      + nonDiscountableOptionsTotal
      + customServiceOptionsPriceTotal;
  } else if (discountMode === "custom") {
    activeDiscountPct = customDiscountPct;
    activeFinalPriceNet =
      discountableBaseNet * (1 - customDiscountPct / 100)
      + nonDiscountableOptionsTotal
      + customServiceOptionsPriceTotal;
  }

  const formatCalculatedPrice = (val: number) => {
      return new Intl.NumberFormat('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val);
  };

  const setCustomDiscountAmountNet = (amountNet: number) => {
    if (discountableBaseNet > 0) {
      const pct = (amountNet / discountableBaseNet) * 100;
      setCustomDiscountPctRaw(pct.toFixed(2));
    } else {
      setCustomDiscountPctRaw("0");
    }
  };

  const activeDiscountAmountNet = discountableBaseNet * (activeDiscountPct / 100);

  return {
    discountMode,
    setDiscountMode,
    customDiscountPctRaw,
    setCustomDiscountPctRaw,
    setCustomDiscountAmountNet,
    activeDiscountAmountNet,
    aiExtractedBasePrice,
    aiBasePriceDeltaPln,
    requireManualPriceReview,
    calculationBlockReason,
    dynamicTotalOptionsPrice,
    totalCatalogPriceNet,
    discountableOptionsTotal,
    nonDiscountableOptionsTotal,
    customServiceOptionsPriceTotal,
    hasOfferFinalPrice,
    isDealerOffer,
    offerDiscountPercentage,
    suggestedDiscountPct,
    suggestedDiscountConfidence,
    activeDiscountPct,
    activeFinalPriceNet,
    formatCalculatedPrice,
    AI_PRICE_ALERT_THRESHOLD_PLN,
  };
}
