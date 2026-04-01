import { useMemo, useState, useCallback } from "react";
import type { FleetVehicleView } from "../types";
import { parsePriceToNumber } from "../components/VehicleTableParts/PriceDualFormat";

export type SortKey =
  | "brand"
  | "model"
  | "samar_category"
  | "fuel"
  | "created_at"
  | "price";

export type SortDir = "asc" | "desc";

export type PriceFilterMode = "catalog" | "discounted";

export interface FilterState {
  sortKey: SortKey;
  sortDir: SortDir;
  dateRange: [number, number]; // timestamps
  priceRange: [number, number];
  priceFilterMode: PriceFilterMode;
  showUnmappedSamarOnly: boolean;

  selectedBrands: string[];
  selectedFuels: string[];
  selectedSamarClasses: string[];
}

function extractSamarCategory(v: FleetVehicleView): string {
  const synth = v.synthesis_data as Record<string, unknown> | undefined;
  if (!synth) return "";
  const mapped = synth.mapped_ai_data as Record<string, string> | undefined;
  if (mapped?.samar_category) return mapped.samar_category;
  const card = synth.card_summary as Record<string, string> | undefined;
  if (card?.samar_category) return card.samar_category;
  return "";
}

function extractFuel(v: FleetVehicleView): string {
  if (v.fuel) return v.fuel;
  const synth = v.synthesis_data as Record<string, unknown> | undefined;
  if (!synth) return "";
  const mapped = synth.mapped_ai_data as Record<string, string> | undefined;
  if (mapped?.fuel) return mapped.fuel;
  const card = synth.card_summary as Record<string, string> | undefined;
  if (card?.fuel) return card.fuel;
  return "";
}

function getBasePrice(v: FleetVehicleView): number {
  return parsePriceToNumber(v.base_price);
}

function getDiscountedPrice(v: FleetVehicleView): number {
  const base = getBasePrice(v);
  const synth = v.synthesis_data as Record<string, unknown> | undefined;
  const pricing = synth?.pricing as Record<string, unknown> | undefined;
  
  if (typeof pricing?.active_final_price_net === "number" && pricing.active_final_price_net > 0) {
    return pricing.active_final_price_net;
  }
  if (typeof v.suggested_discount_pct === "number" && v.suggested_discount_pct > 0) {
    return base * (1 - v.suggested_discount_pct);
  }
  return base; // Fallback to catalog if no discount found
}

// Minimum price threshold — below this it's noise (e.g. percentage, code, etc.)
const MIN_VALID_PRICE = 1000;

function computeAggregates(vehicles: FleetVehicleView[]) {
  if (vehicles.length === 0) {
    const now = Date.now();
    return { 
      dateMin: now, dateMax: now, 
      catalogPriceMin: 0, catalogPriceMax: 0,
      discountPriceMin: 0, discountPriceMax: 0,
      brands: [] as string[],
      fuels: [] as string[],
      samarClasses: [] as string[],
    };
  }

  let dateMin = Infinity;
  let dateMax = -Infinity;
  let catalogPriceMin = Infinity;
  let catalogPriceMax = -Infinity;
  let discountPriceMin = Infinity;
  let discountPriceMax = -Infinity;

  const brandsSet = new Set<string>();
  const fuelsSet = new Set<string>();
  const samarSet = new Set<string>();

  for (const v of vehicles) {
    const ts = new Date(v.created_at).getTime();
    if (ts < dateMin) dateMin = ts;
    if (ts > dateMax) dateMax = ts;

    const catPrice = getBasePrice(v);
    if (catPrice >= MIN_VALID_PRICE) {
      if (catPrice < catalogPriceMin) catalogPriceMin = catPrice;
      if (catPrice > catalogPriceMax) catalogPriceMax = catPrice;
    }

    const discPrice = getDiscountedPrice(v);
    if (discPrice >= MIN_VALID_PRICE) {
      if (discPrice < discountPriceMin) discountPriceMin = discPrice;
      if (discPrice > discountPriceMax) discountPriceMax = discPrice;
    }

    if (v.brand) brandsSet.add(v.brand);
    
    const f = extractFuel(v);
    if (f) fuelsSet.add(f);

    const s = extractSamarCategory(v);
    if (s) samarSet.add(s);
  }

  if (catalogPriceMin === Infinity) catalogPriceMin = 0;
  if (catalogPriceMax === -Infinity) catalogPriceMax = 0;
  if (discountPriceMin === Infinity) discountPriceMin = 0;
  if (discountPriceMax === -Infinity) discountPriceMax = 0;

  // Align date bounds to full-day boundaries so the slider step (86400000ms)
  // divides evenly into the range and thumbs can reach both ends of the track.
  const DAY_MS = 86400000;
  dateMin = Math.floor(dateMin / DAY_MS) * DAY_MS;
  dateMax = Math.ceil(dateMax / DAY_MS) * DAY_MS;

  return { 
    dateMin, dateMax, 
    catalogPriceMin, catalogPriceMax,
    discountPriceMin, discountPriceMax,
    brands: Array.from(brandsSet).sort(),
    fuels: Array.from(fuelsSet).sort(),
    samarClasses: Array.from(samarSet).sort()
  };
}

export function useVehicleFilters(vehicles: FleetVehicleView[]) {
  const aggregates = useMemo(() => computeAggregates(vehicles), [vehicles]);

  const [filters, setFilters] = useState<FilterState>({
    sortKey: "created_at",
    sortDir: "desc",
    dateRange: [0, Infinity],
    priceRange: [0, Infinity],
    priceFilterMode: "catalog",
    showUnmappedSamarOnly: false,
    selectedBrands: [],
    selectedFuels: [],
    selectedSamarClasses: []
  });

  const activeDateRange = useMemo<[number, number]>(
    () => [
      filters.dateRange[0] <= 0 ? aggregates.dateMin : filters.dateRange[0],
      filters.dateRange[1] >= Infinity ? aggregates.dateMax : filters.dateRange[1],
    ],
    [filters.dateRange, aggregates.dateMin, aggregates.dateMax],
  );

  const currentModePriceMin = filters.priceFilterMode === "catalog" ? aggregates.catalogPriceMin : aggregates.discountPriceMin;
  const currentModePriceMax = filters.priceFilterMode === "catalog" ? aggregates.catalogPriceMax : aggregates.discountPriceMax;

  const activePriceRange = useMemo<[number, number]>(
    () => [
        filters.priceRange[0] <= 0 ? currentModePriceMin : filters.priceRange[0],
        filters.priceRange[1] >= Infinity ? currentModePriceMax : filters.priceRange[1]
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filters.priceRange, currentModePriceMin, currentModePriceMax, filters.priceFilterMode]
  );

  const setSortKey = useCallback((key: SortKey) => {
    setFilters((prev) => ({
      ...prev,
      sortKey: key,
      sortDir: prev.sortKey === key && prev.sortDir === "asc" ? "desc" : "asc",
    }));
  }, []);

  const setDateRange = useCallback((range: [number, number]) => {
    setFilters((prev) => ({ ...prev, dateRange: range }));
  }, []);

  const setPriceRange = useCallback((range: [number, number]) => {
    setFilters((prev) => ({ ...prev, priceRange: range }));
  }, []);

  const setSelectedBrands = useCallback((brands: string[]) => {
      setFilters(prev => ({ ...prev, selectedBrands: brands }));
  }, []);

  const setSelectedFuels = useCallback((fuels: string[]) => {
      setFilters(prev => ({ ...prev, selectedFuels: fuels }));
  }, []);

  const setSelectedSamarClasses = useCallback((classes: string[]) => {
      setFilters(prev => ({ ...prev, selectedSamarClasses: classes }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      sortKey: "created_at",
      sortDir: "desc",
      dateRange: [0, Infinity],
      priceRange: [0, Infinity],
      priceFilterMode: "catalog",
      showUnmappedSamarOnly: false,
      selectedBrands: [],
      selectedFuels: [],
      selectedSamarClasses: []
    });
  }, []);

  const filteredVehicles = useMemo(() => {
    let result = [...vehicles];

    // Filter by Brand
    if (filters.selectedBrands.length > 0) {
      result = result.filter(v => v.brand && filters.selectedBrands.includes(v.brand));
    }

    // Filter by Fuel
    if (filters.selectedFuels.length > 0) {
      result = result.filter(v => {
          const f = extractFuel(v);
          return f && filters.selectedFuels.includes(f);
      });
    }

    // Filter by SAMAR Class
    if (filters.selectedSamarClasses.length > 0) {
      result = result.filter(v => {
          const sc = extractSamarCategory(v);
          return sc && filters.selectedSamarClasses.includes(sc);
      });
    }

    // Filter unmapped SAMAR
    if (filters.showUnmappedSamarOnly) {
      result = result.filter((v) => {
        const synth = v.synthesis_data as Record<string, unknown> | undefined;
        return !synth || !synth.samar_class_id || synth.samar_class_id === "";
      });
    }

    // Date range filter
    const [dMin, dMax] = activeDateRange;
    result = result.filter((v) => {
      const ts = new Date(v.created_at).getTime();
      return ts >= dMin && ts <= dMax;
    });

    // Price range filter
    const [pMin, pMax] = activePriceRange;
    if (pMin > 0 || pMax < Infinity) {
      result = result.filter((v) => {
        const price = filters.priceFilterMode === "catalog" ? getBasePrice(v) : getDiscountedPrice(v);
        if (price === 0) return true; // Keep unpriced
        return price >= pMin && price <= pMax;
      });
    }

    // Sorting
    const dir = filters.sortDir === "asc" ? 1 : -1;
    result.sort((a, b) => {
      let cmp = 0;
      switch (filters.sortKey) {
        case "brand":
          cmp = (a.brand || "").localeCompare(b.brand || "", "pl");
          break;
        case "model":
          cmp = (a.model || "").localeCompare(b.model || "", "pl");
          break;
        case "samar_category":
          cmp = extractSamarCategory(a).localeCompare(
            extractSamarCategory(b),
            "pl",
          );
          break;
        case "fuel":
          cmp = extractFuel(a).localeCompare(extractFuel(b), "pl");
          break;
        case "created_at":
          cmp =
            new Date(a.created_at).getTime() -
            new Date(b.created_at).getTime();
          break;
        case "price":
          cmp = getBasePrice(a) - getBasePrice(b);
          break;
      }
      return cmp * dir;
    });

    return result;
  }, [vehicles, filters, activeDateRange, activePriceRange]);

  const setShowUnmappedSamarOnly = useCallback((val: boolean) => {
    setFilters((prev) => ({ ...prev, showUnmappedSamarOnly: val }));
  }, []);

  return {
    filters,
    aggregates,
    activeDateRange,
    activePriceRange,
    currentModePriceMin,
    currentModePriceMax,
    filteredVehicles,
    setSortKey,
    setDateRange,
    setPriceRange,
    setSelectedBrands,
    setSelectedFuels,
    setSelectedSamarClasses,
    setShowUnmappedSamarOnly,
    resetFilters,
  };
}
