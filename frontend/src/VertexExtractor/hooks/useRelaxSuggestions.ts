import { useCallback, useState } from "react";
import { API_BASE_URL } from "../../config/env";
import { apiClient } from "../../lib/apiClient";
import type { SearchFilter } from "../types";

export type RelaxableFilterKind =
  | "feature"
  | "bodyType"
  | "vehicleScope"
  | "priceMin"
  | "priceMax";

export type RelaxSuggestion = {
  kind: RelaxableFilterKind;
  /** Stable identifier for this filter (feature_key for features, body type name for bodyTypes). */
  id: string;
  /** Human-readable label shown in UI. */
  label: string;
  /** Number of vehicles that the search would return if THIS one filter were removed. */
  wouldUnlockCount: number;
  /** Action callback that the UI invokes to actually remove the filter. */
  remove: () => void;
};

export type RelaxInput = {
  globalSearchQuery: string;
  activeFilters: SearchFilter[];
  bodyTypes: string[];
  vehicleScope: "all" | "passenger" | "commercial";
  priceMin: number | "";
  priceMax: number | "";
  priceMonths: number;
  priceMileage: number;
  priceDepositPct: number;
  setActiveFilters: (next: SearchFilter[]) => void;
  setBodyTypes: (next: string[]) => void;
  setVehicleScope: (next: "all" | "passenger" | "commercial") => void;
  setPriceMin: (next: number | "") => void;
  setPriceMax: (next: number | "") => void;
};

type SearchPayload = {
  search_query?: string;
  filters: { feature_key: string; value_bool?: boolean; value_num_min?: number; value_num_max?: number; value_text?: string }[];
  body_types?: string[];
  vehicle_scope?: string;
  limit: number;
  offset: number;
  price_min?: number;
  price_max?: number;
  price_months: number;
  price_mileage: number;
  price_deposit_pct: number;
};

function buildPayload(s: RelaxInput, overrides: Partial<RelaxInput> = {}): SearchPayload {
  const merged = { ...s, ...overrides };
  return {
    search_query: merged.globalSearchQuery.trim() || undefined,
    filters: merged.activeFilters.map((f) => ({
      feature_key: f.feature_key,
      value_bool: f.value_bool,
      value_num_min: f.value_num_min,
      value_num_max: f.value_num_max,
      value_text: f.value_text,
    })),
    body_types: merged.bodyTypes.length > 0 ? merged.bodyTypes : undefined,
    vehicle_scope: merged.vehicleScope !== "all" ? merged.vehicleScope : undefined,
    limit: 1,
    offset: 0,
    price_min: merged.priceMin !== "" ? Number(merged.priceMin) : undefined,
    price_max: merged.priceMax !== "" ? Number(merged.priceMax) : undefined,
    price_months: merged.priceMonths,
    price_mileage: merged.priceMileage,
    price_deposit_pct: merged.priceDepositPct,
  };
}

async function countResults(payload: SearchPayload, signal?: AbortSignal): Promise<number> {
  try {
    const res = await apiClient.fetch(`${API_BASE_URL}/api/features/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
      skipGlobalError: true,
    });
    if (!res.ok) return -1;
    const data = await res.json();
    return typeof data.total_count === "number" ? data.total_count : 0;
  } catch {
    return -1;
  }
}

export function useRelaxSuggestions() {
  const [suggestions, setSuggestions] = useState<RelaxSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compute = useCallback(async (input: RelaxInput) => {
    setLoading(true);
    setError(null);

    const probes: Promise<RelaxSuggestion | null>[] = [];

    input.activeFilters.forEach((f) => {
      const probe = countResults(
        buildPayload(input, {
          activeFilters: input.activeFilters.filter((x) => x.feature_key !== f.feature_key),
        })
      ).then<RelaxSuggestion | null>((n) =>
        n < 0
          ? null
          : {
              kind: "feature",
              id: f.feature_key,
              label: f.display_name || f.feature_key,
              wouldUnlockCount: n,
              remove: () =>
                input.setActiveFilters(
                  input.activeFilters.filter((x) => x.feature_key !== f.feature_key)
                ),
            }
      );
      probes.push(probe);
    });

    input.bodyTypes.forEach((bt) => {
      const probe = countResults(
        buildPayload(input, { bodyTypes: input.bodyTypes.filter((x) => x !== bt) })
      ).then<RelaxSuggestion | null>((n) =>
        n < 0
          ? null
          : {
              kind: "bodyType",
              id: bt,
              label: `Nadwozie: ${bt}`,
              wouldUnlockCount: n,
              remove: () =>
                input.setBodyTypes(input.bodyTypes.filter((x) => x !== bt)),
            }
      );
      probes.push(probe);
    });

    if (input.vehicleScope !== "all") {
      const probe = countResults(
        buildPayload(input, { vehicleScope: "all" })
      ).then<RelaxSuggestion | null>((n) =>
        n < 0
          ? null
          : {
              kind: "vehicleScope",
              id: "scope",
              label:
                input.vehicleScope === "passenger"
                  ? "Tylko osobowe"
                  : "Tylko ciężarowe/dostawcze",
              wouldUnlockCount: n,
              remove: () => input.setVehicleScope("all"),
            }
      );
      probes.push(probe);
    }

    if (input.priceMin !== "") {
      const probe = countResults(
        buildPayload(input, { priceMin: "" })
      ).then<RelaxSuggestion | null>((n) =>
        n < 0
          ? null
          : {
              kind: "priceMin",
              id: "priceMin",
              label: `Cena od ${input.priceMin} PLN`,
              wouldUnlockCount: n,
              remove: () => input.setPriceMin(""),
            }
      );
      probes.push(probe);
    }

    if (input.priceMax !== "") {
      const probe = countResults(
        buildPayload(input, { priceMax: "" })
      ).then<RelaxSuggestion | null>((n) =>
        n < 0
          ? null
          : {
              kind: "priceMax",
              id: "priceMax",
              label: `Cena do ${input.priceMax} PLN`,
              wouldUnlockCount: n,
              remove: () => input.setPriceMax(""),
            }
      );
      probes.push(probe);
    }

    try {
      const results = (await Promise.all(probes)).filter(
        (r): r is RelaxSuggestion => r !== null && r.wouldUnlockCount > 0
      );
      results.sort((a, b) => b.wouldUnlockCount - a.wouldUnlockCount);
      setSuggestions(results);
    } catch (err) {
      console.error("Relax suggestions failed:", err);
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setSuggestions([]);
    setError(null);
  }, []);

  return { suggestions, loading, error, compute, reset };
}
