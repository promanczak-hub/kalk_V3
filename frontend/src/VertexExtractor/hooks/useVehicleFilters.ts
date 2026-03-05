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

interface FilterState {
  sortKey: SortKey;
  sortDir: SortDir;
  dateRange: [number, number]; // timestamps
  priceRange: [number, number];
  liveSearchText: string;
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

// Minimum price threshold — below this it's noise (e.g. percentage, code, etc.)
const MIN_VALID_PRICE = 1000;

function computeBounds(vehicles: FleetVehicleView[]) {
  if (vehicles.length === 0) {
    const now = Date.now();
    return { dateMin: now, dateMax: now, priceMin: 0, priceMax: 0 };
  }

  let dateMin = Infinity;
  let dateMax = -Infinity;
  let priceMin = Infinity;
  let priceMax = -Infinity;

  for (const v of vehicles) {
    const ts = new Date(v.created_at).getTime();
    if (ts < dateMin) dateMin = ts;
    if (ts > dateMax) dateMax = ts;

    const price = parsePriceToNumber(v.base_price);
    if (price >= MIN_VALID_PRICE) {
      if (price < priceMin) priceMin = price;
      if (price > priceMax) priceMax = price;
    }
  }

  if (priceMin === Infinity) priceMin = 0;
  if (priceMax === -Infinity) priceMax = 0;

  // Align date bounds to full-day boundaries so the slider step (86400000ms)
  // divides evenly into the range and thumbs can reach both ends of the track.
  const DAY_MS = 86400000;
  dateMin = Math.floor(dateMin / DAY_MS) * DAY_MS;
  dateMax = Math.ceil(dateMax / DAY_MS) * DAY_MS;

  return { dateMin, dateMax, priceMin, priceMax };
}

export function useVehicleFilters(vehicles: FleetVehicleView[]) {
  const bounds = useMemo(() => computeBounds(vehicles), [vehicles]);

  const [filters, setFilters] = useState<FilterState>({
    sortKey: "created_at",
    sortDir: "desc",
    dateRange: [0, Infinity],
    priceRange: [0, Infinity],
    liveSearchText: "",
  });

  const activeDateRange = useMemo<[number, number]>(
    () => [
      filters.dateRange[0] <= 0 ? bounds.dateMin : filters.dateRange[0],
      filters.dateRange[1] >= Infinity ? bounds.dateMax : filters.dateRange[1],
    ],
    [filters.dateRange, bounds.dateMin, bounds.dateMax],
  );

  const activePriceRange = useMemo<[number, number]>(
    () => [
      filters.priceRange[0] <= 0 ? bounds.priceMin : filters.priceRange[0],
      filters.priceRange[1] >= Infinity
        ? bounds.priceMax
        : filters.priceRange[1],
    ],
    [filters.priceRange, bounds.priceMin, bounds.priceMax],
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

  const setLiveSearchText = useCallback((text: string) => {
    setFilters((prev) => ({ ...prev, liveSearchText: text }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      sortKey: "created_at",
      sortDir: "desc",
      dateRange: [0, Infinity],
      priceRange: [0, Infinity],
      liveSearchText: "",
    });
  }, []);

  const filteredVehicles = useMemo(() => {
    let result = [...vehicles];

    // Live search — tokenize and filter
    const searchText = filters.liveSearchText.trim().toLowerCase();
    if (searchText.length >= 2) {
      const tokens = searchText.split(/\s+/).filter((t) => t.length >= 2);
      if (tokens.length > 0) {
        result = result.filter((v) => {
          const haystack = JSON.stringify(v).toLowerCase();
          return tokens.every((token) => haystack.includes(token));
        });
      }
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
        const price = parsePriceToNumber(v.base_price);
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
          cmp =
            parsePriceToNumber(a.base_price) - parsePriceToNumber(b.base_price);
          break;
      }
      return cmp * dir;
    });

    return result;
  }, [vehicles, filters, activeDateRange, activePriceRange]);

  return {
    filters,
    bounds,
    activeDateRange,
    activePriceRange,
    filteredVehicles,
    setSortKey,
    setDateRange,
    setPriceRange,
    setLiveSearchText,
    resetFilters,
  };
}
