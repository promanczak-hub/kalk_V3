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
  selectedBodyTypes: string[];
  selectedTransmissions: string[];
  selectedDrives: string[];
  powerRange: [number, number];
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
  let raw = "";
  if (v.fuel) raw = v.fuel;
  else {
    const synth = v.synthesis_data as Record<string, unknown> | undefined;
    if (synth) {
      const mapped = synth.mapped_ai_data as Record<string, string> | undefined;
      if (mapped?.fuel) raw = mapped.fuel;
      else {
        const card = synth.card_summary as Record<string, string> | undefined;
        if (card?.fuel) raw = card.fuel;
      }
    }
  }

  if (!raw) return "";

  const low = raw.toLowerCase().trim();

  // 1. Wodór (FCEV)
  if (low.includes("wodór") || low.includes("fcev") || low.includes("hydrogen")) return "Wodór (FCEV)";

  // 2. Plug-in Hybrid (PHEV)
  if (low.includes("phev") || low.includes("plug-in") || low.includes("plugin") || low.includes("plug in")) return "Plug-in Hybrid (PHEV)";
  
  // 3. i 4. mHEV (Diesel / Benzyna)
  if (low.includes("mhev") || low.includes("mild") || low.includes("mięk")) {
    if (low.includes("diesel") || low.includes("olej") || low.includes(" on") || low === "on") {
      return "Diesel mHEV (ON-mHEV)";
    }
    return "Benzyna mHEV (PB-mHEV)";
  }
  
  // 5. Hybryda (HEV)
  if (low.includes("hev") || low.includes("hybryd") || low.includes("hybrid")) return "Hybryda (HEV)";
  
  // 6. LPG
  if (low.includes("lpg") || low.includes("gaz")) return "LPG";
  
  // 7. Elektryczny (BEV)
  if (low.includes("elektr") || low.includes("bev") || low === "ev") return "Elektryczny (BEV)";
  
  // 8. Diesel (ON)
  if (low.includes("diesel") || low.includes("olej nap") || low === "on" || low.includes(" on")) return "Diesel (ON)";
  
  // 9. Benzyna (PB)
  if (low.includes("benzyna") || low.includes("petrol") || low === "pb" || low.includes("pb")) return "Benzyna (PB)";

  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function extractBodyType(v: FleetVehicleView): string {
  let raw = "";
  if (v.body_style) raw = v.body_style;
  else {
    const synth = v.synthesis_data as Record<string, unknown> | undefined;
    if (synth) {
      const mapped = synth.mapped_ai_data as Record<string, string> | undefined;
      if (mapped?.body_type) raw = mapped.body_type;
    }
  }
  
  if (!raw) return "";

  const low = raw.toLowerCase();
  if (low.includes("suv") || low.includes("crossover") || low.includes("sav")) return "SUV";
  if (low.includes("kombi") || low.includes("station wagon") || low.includes("touring") || low.includes("estate") || low.includes("variant") || low.includes("shooting brake")) return "Kombi";
  if (low.includes("sedan") || low.includes("limuzyna") || low.includes("saloon")) return "Limuzyna";
  if (low.includes("hatchback") || low.includes("compact")) return "Hatchback";
  if (low.includes("liftback") || low.includes("sportback") || low.includes("fastback")) return "Liftback";
  if (low.includes("furgon") || low.includes("van") || low.includes("bus")) return "Furgon";
  if (low.includes("avant")) return "Avant";
  if (low.includes("coupe") || low.includes("coupé")) return "Coupe";
  if (low.includes("cabrio") || low.includes("kabriolet") || low.includes("spider") || low.includes("roadster")) return "Cabrio";
  if (low.includes("pickup") || low.includes("pick-up")) return "Pickup";
  if (low.includes("minivan") || low.includes("mpv")) return "Minivan";

  // capitalize first char
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function extractTransmission(v: FleetVehicleView): string {
  let raw = "";
  if (v.transmission) raw = v.transmission;
  else {
    const synth = v.synthesis_data as Record<string, unknown> | undefined;
    if (synth) {
      const mapped = synth.mapped_ai_data as Record<string, string> | undefined;
      if (mapped?.transmission) raw = mapped.transmission;
      else {
        const card = synth.card_summary as Record<string, string> | undefined;
        if (card?.transmission) raw = card.transmission;
      }
    }
  }

  if (!raw) return "";

  const low = raw.toLowerCase();
  
  // Checking for automatic variants
  if (
    low.includes("aut") || 
    low.includes("dsg") || 
    low.includes("cvt") || 
    low.includes("dct") || 
    low.includes("pdk") || 
    low.includes("stronic") || 
    low.includes("s-tronic") ||
    low.includes("s tronic") ||
    low.includes("tronic") ||
    low.includes("edc") || 
    low.includes("eat") ||
    low.includes("7-biegowa") ||
    low.includes("8-biegowa") ||
    low.includes("9-biegowa")
  ) {
    // some manual strings might contain "biegowa" but usually they are prefixed with "manualna" 
    // let's explicitly look for manual first for safety
  }

  if (low.includes("man") || low.includes("ręcz") || low.includes("manualna")) {
    return "Manualna";
  }

  // Double check if it matches automatic patterns
  if (
    low.includes("aut") || 
    low.includes("dsg") || 
    low.includes("cvt") || 
    low.includes("dct") || 
    low.includes("pdk") || 
    low.includes("stronic") || 
    low.includes("s-tronic") ||
    low.includes("s tronic") ||
    low.includes("tronic") ||
    low.includes("edc") || 
    low.includes("eat")
  ) {
    return "Automatyczna";
  }

  // fallback logic: if it has "biegowa" and we didn't return manual above
  // we assume it's automatic since in premium cars list almost all are auto unless specified as manual
  if (low.includes("biegowa") || low.includes("biegowy") || low.includes("stopniowa")) {
    return "Automatyczna";
  }

  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function extractDriveType(v: FleetVehicleView): string {
  let raw = "";
  if (v.drive_type) raw = v.drive_type;
  else {
    const synth = v.synthesis_data as Record<string, unknown> | undefined;
    if (synth) {
      const mapped = synth.mapped_ai_data as Record<string, string> | undefined;
      if (mapped?.drive_type) raw = mapped.drive_type;
      else if (mapped?.drivetrain) raw = mapped.drivetrain;
      else {
        const card = synth.card_summary as Record<string, string> | undefined;
        if (card?.drive_type) raw = card.drive_type;
      }
    }
  }

  if (!raw) return "";

  const low = raw.toLowerCase();
  
  if (low.includes("fwd") || low.includes("4x2") || low.includes("przód") || low.includes("przedni")) return "FWD";
  if (low.includes("awd") || low.includes("4x4") || low.includes("quattro") || low.includes("xdrive") || low.includes("4matic") || low.includes("all4")) return "AWD";
  if (low.includes("rwd") || low.includes("tył") || low.includes("tylni") || low.includes("tylny")) return "RWD";

  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function extractPower(v: FleetVehicleView): number {
  const synth = v.synthesis_data as Record<string, unknown> | undefined;
  const card = synth?.card_summary as Record<string, unknown> | undefined;
  if (typeof card?.power_hp === 'number') return card.power_hp;
  if (typeof card?.power_hp === 'string') {
     const parsed = parseFloat(card.power_hp);
     if (!isNaN(parsed)) return parsed;
  }
  return 0; 
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
      bodyTypes: [] as string[],
      transmissions: [] as string[],
      drives: [] as string[],
      powerMin: 0, powerMax: 0,
    };
  }

  let dateMin = Infinity;
  let dateMax = -Infinity;
  let catalogPriceMin = Infinity;
  let catalogPriceMax = -Infinity;
  let discountPriceMin = Infinity;
  let discountPriceMax = -Infinity;
  let powerMin = Infinity;
  let powerMax = -Infinity;

  const brandsSet = new Set<string>();
  const fuelsSet = new Set<string>();
  const samarSet = new Set<string>();
  const bodyTypesSet = new Set<string>();
  const transmissionsSet = new Set<string>();
  const drivesSet = new Set<string>();

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

    const b = extractBodyType(v);
    if (b) bodyTypesSet.add(b);

    const trans = extractTransmission(v);
    if (trans) transmissionsSet.add(trans);

    const drv = extractDriveType(v);
    if (drv) drivesSet.add(drv);

    const pow = extractPower(v);
    if (pow > 0) {
      if (pow < powerMin) powerMin = pow;
      if (pow > powerMax) powerMax = pow;
    }
  }

  if (catalogPriceMin === Infinity) catalogPriceMin = 0;
  if (catalogPriceMax === -Infinity) catalogPriceMax = 0;
  if (discountPriceMin === Infinity) discountPriceMin = 0;
  if (discountPriceMax === -Infinity) discountPriceMax = 0;
  if (powerMin === Infinity) powerMin = 0;
  if (powerMax === -Infinity) powerMax = 0;

  // Align date bounds to full-day boundaries so the slider step (86400000ms)
  // divides evenly into the range and thumbs can reach both ends of the track.
  const DAY_MS = 86400000;
  dateMin = Math.floor(dateMin / DAY_MS) * DAY_MS;
  dateMax = Math.ceil(dateMax / DAY_MS) * DAY_MS;

  return { 
    dateMin, dateMax, 
    catalogPriceMin, catalogPriceMax,
    discountPriceMin, discountPriceMax,
    powerMin, powerMax,
    brands: Array.from(brandsSet).sort(),
    fuels: Array.from(fuelsSet).sort(),
    samarClasses: Array.from(samarSet).sort(),
    bodyTypes: Array.from(bodyTypesSet).sort(),
    transmissions: Array.from(transmissionsSet).sort(),
    drives: Array.from(drivesSet).sort()
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
    selectedSamarClasses: [],
    selectedBodyTypes: [],
    selectedTransmissions: [],
    selectedDrives: [],
    powerRange: [0, Infinity]
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

  const activePowerRange = useMemo<[number, number]>(
    () => [
        filters.powerRange[0] <= 0 ? aggregates.powerMin : filters.powerRange[0],
        filters.powerRange[1] >= Infinity ? aggregates.powerMax : filters.powerRange[1]
    ],
    [filters.powerRange, aggregates.powerMin, aggregates.powerMax]
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

  const setSelectedBodyTypes = useCallback((types: string[]) => {
      setFilters(prev => ({ ...prev, selectedBodyTypes: types }));
  }, []);

  const setSelectedTransmissions = useCallback((transmissions: string[]) => {
      setFilters(prev => ({ ...prev, selectedTransmissions: transmissions }));
  }, []);

  const setSelectedDrives = useCallback((drives: string[]) => {
      setFilters(prev => ({ ...prev, selectedDrives: drives }));
  }, []);

  const setPowerRange = useCallback((range: [number, number]) => {
      setFilters((prev) => ({ ...prev, powerRange: range }));
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
      selectedSamarClasses: [],
      selectedBodyTypes: [],
      selectedTransmissions: [],
      selectedDrives: [],
      powerRange: [0, Infinity]
    });
  }, []);

  const filteredVehicles = useMemo(() => {
    let result = [...vehicles];

    // Filter by Brand
    if (filters.selectedBrands?.length > 0) {
      result = result.filter(v => v.brand && filters.selectedBrands.includes(v.brand));
    }

    // Filter by Fuel
    if (filters.selectedFuels?.length > 0) {
      result = result.filter(v => {
          const f = extractFuel(v);
          return f && filters.selectedFuels.includes(f);
      });
    }

    // Filter by SAMAR Class
    if (filters.selectedSamarClasses?.length > 0) {
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

    // Filter by Body Type
    if (filters.selectedBodyTypes?.length > 0) {
      result = result.filter(v => {
          const b = extractBodyType(v);
          return b && filters.selectedBodyTypes.includes(b);
      });
    }

    // Filter by Transmission
    const selectedTransmissions = filters.selectedTransmissions || [];
    if (selectedTransmissions.length > 0) {
      result = result.filter(v => {
          const t = extractTransmission(v);
          return t && selectedTransmissions.includes(t);
      });
    }

    // Filter by Drive Type
    const selectedDrives = filters.selectedDrives || [];
    if (selectedDrives.length > 0) {
      result = result.filter(v => {
          const drv = extractDriveType(v);
          return drv && selectedDrives.includes(drv);
      });
    }

    // Power range filter
    const [powMin, powMax] = activePowerRange;
    if (powMin > 0 || powMax < Infinity) {
      result = result.filter((v) => {
        const p = extractPower(v);
        if (p === 0) return true; // Keep unspecified if you want, or require it
        return p >= powMin && p <= powMax;
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
  }, [vehicles, filters, activeDateRange, activePriceRange, activePowerRange]);

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
    activePowerRange,
    setSelectedBodyTypes,
    setSelectedTransmissions,
    setSelectedDrives,
    setPowerRange,
  };
}
