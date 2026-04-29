import { useState, useCallback, useEffect } from "react";
import { API_BASE_URL } from "../../config/env";
import type { CatalogCategory, SearchFilter, SearchResult, CatalogFeature } from "../types";
import { apiClient } from "../../lib/apiClient";

export function useReverseSearch() {
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [activeFilters, setActiveFilters] = useState<SearchFilter[]>([]);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());
  const [facets, setFacets] = useState<Record<string, number>>({});
  const [hasSearched, setHasSearched] = useState(false);
  const [vehicleScope, setVehicleScope] = useState<"all" | "passenger" | "commercial">("all");
  const [bodyTypes, setBodyTypes] = useState<string[]>([]);
  const [bodyTypeSearch, setBodyTypeSearch] = useState("");
  const [showBodyTypeDropdown, setShowBodyTypeDropdown] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [dbBodyTypes, setDbBodyTypes] = useState<string[]>([]);

  // Search Queries
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [featureSearchQuery, setFeatureSearchQuery] = useState("");

  // Price configuration state
  const [priceMin, setPriceMin] = useState<number | "">("");
  const [priceMax, setPriceMax] = useState<number | "">("");
  const [priceMonths, setPriceMonths] = useState<number>(48);
  const [priceMileage, setPriceMileage] = useState<number>(20000);
  const [priceDepositPct, setPriceDepositPct] = useState<number>(0);
  const [priceMarginPct, setPriceMarginPct] = useState<number | "">("");

  const baseUrl = API_BASE_URL;

  // Fetch catalog
  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        const res = await apiClient.fetch(`${baseUrl}/api/features/catalog`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setCatalog(
          data.categories.filter((c: CatalogCategory) => c.features.length > 0)
        );
      } catch (err) {
        console.error("Failed to fetch catalog:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchCatalog();
  }, [baseUrl]);

  // Fetch body types from DB — single source of truth
  useEffect(() => {
    const fetchBodyTypes = async () => {
      try {
        const res = await apiClient.fetch(`${baseUrl}/api/body-types`);
        if (res.ok) {
          const data = await res.json();
          setDbBodyTypes(Array.isArray(data) ? data.map((bt: { name: string }) => bt.name) : []);
        }
      } catch (err) {
        console.error("Failed to fetch body types:", err);
      }
    };
    fetchBodyTypes();
  }, [baseUrl]);

  // Set feature filter value
  const setFeatureFilter = useCallback((feature: CatalogFeature, field: keyof SearchFilter, value: string | number | boolean | undefined) => {
    setActiveFilters((prev) => {
      const existing = prev.find((f) => f.feature_key === feature.feature_key);
      
      let newFilters = [...prev];
      if (existing) {
        newFilters = newFilters.map(f => {
          if (f.feature_key === feature.feature_key) {
             return { ...f, [field]: value };
          }
          return f;
        });
      } else {
        newFilters.push({
          feature_key: feature.feature_key,
          display_name: feature.display_name,
          [field]: value 
        });
      }

      // Cleanup step: remove filters that have NO values
      return newFilters.filter(f => 
        f.value_bool !== undefined || 
        f.value_num_min !== undefined || 
        f.value_num_max !== undefined || 
        (f.value_text !== undefined && f.value_text !== "")
      );
    });
  }, []);

  // Search
  const runSearch = useCallback(async () => {
    if (globalSearchQuery.trim() === "" && activeFilters.length === 0 && bodyTypes.length === 0 && vehicleScope === "all" && priceMin === "" && priceMax === "") {
        setResults([]);
        setTotalCount(0);
        return;
    }
    setSearching(true);
    setHasSearched(true);
    try {
      const res = await apiClient.fetch(`${baseUrl}/api/features/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search_query: globalSearchQuery.trim() !== "" ? globalSearchQuery.trim() : undefined,
          filters: activeFilters.map((f) => ({
            feature_key: f.feature_key,
            value_bool: f.value_bool,
            value_num_min: f.value_num_min,
            value_num_max: f.value_num_max,
            value_text: f.value_text,
          })),
          body_types: bodyTypes.length > 0 ? bodyTypes : undefined,
          vehicle_scope: vehicleScope !== "all" ? vehicleScope : undefined,
          limit: 50,
          offset: 0,
          price_min: priceMin !== "" ? Number(priceMin) : undefined,
          price_max: priceMax !== "" ? Number(priceMax) : undefined,
          price_months: priceMonths,
          price_mileage: priceMileage,
          price_deposit_pct: priceDepositPct,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.results);
      setTotalCount(data.total_count);
      setFacets(data.facets || {});
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  }, [activeFilters, bodyTypes, vehicleScope, baseUrl, priceMin, priceMax, priceMonths, priceMileage, priceDepositPct, priceMarginPct, globalSearchQuery]);

  // Auto-run search when filters change with debounce
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      runSearch();
    }, 600); // Debounce set to 600ms as requested previously

    return () => clearTimeout(delayDebounceFn);
  }, [runSearch]);

  const clearFilters = () => {
    setActiveFilters([]);
    setBodyTypes([]);
    setVehicleScope("all");
    setPriceMin("");
    setPriceMax("");
    setPriceMonths(48);
    setPriceMileage(20000);
    setPriceDepositPct(0);
    setPriceMarginPct("");
    setResults([]);
    setTotalCount(0);
    setFacets({});
    setHasSearched(false);
    setGlobalSearchQuery("");
    setFeatureSearchQuery("");
  };

  const loadFilterState = useCallback((s: {
    globalSearchQuery?: string;
    activeFilters?: SearchFilter[];
    bodyTypes?: string[];
    vehicleScope?: "all" | "passenger" | "commercial";
    priceMin?: number | "";
    priceMax?: number | "";
    priceMonths?: number;
    priceMileage?: number;
    priceDepositPct?: number;
    priceMarginPct?: number | "";
  }) => {
    setGlobalSearchQuery(s.globalSearchQuery ?? "");
    setActiveFilters(Array.isArray(s.activeFilters) ? s.activeFilters : []);
    setBodyTypes(Array.isArray(s.bodyTypes) ? s.bodyTypes : []);
    setVehicleScope(s.vehicleScope ?? "all");
    setPriceMin(s.priceMin ?? "");
    setPriceMax(s.priceMax ?? "");
    setPriceMonths(typeof s.priceMonths === "number" ? s.priceMonths : 48);
    setPriceMileage(typeof s.priceMileage === "number" ? s.priceMileage : 20000);
    setPriceDepositPct(typeof s.priceDepositPct === "number" ? s.priceDepositPct : 0);
    setPriceMarginPct(s.priceMarginPct ?? "");
  }, []);

  const handleExtractionSuccess = useCallback((
    extractedFilters: SearchFilter[], 
    newExpandedCats: Set<string>,
    financials?: { price_max?: number | null; duration_months?: number | null; annual_mileage?: number | null }
  ) => {
    setActiveFilters(prev => {
        const merged = [...prev];
        extractedFilters.forEach(newFilter => {
            if (!merged.some(f => f.feature_key === newFilter.feature_key)) {
                merged.push(newFilter);
            }
        });
        return merged;
    });
    setExpandedCats(prev => {
        const merged = new Set(prev);
        newExpandedCats.forEach(cat => merged.add(cat));
        return merged;
    });

    if (financials) {
        if (financials.price_max) setPriceMax(financials.price_max);
        if (financials.duration_months) setPriceMonths(financials.duration_months);
        if (financials.annual_mileage) setPriceMileage(financials.annual_mileage);
    }
  }, []);

  return {
    state: {
      catalog, loading, searching, results, totalCount, activeFilters, expandedCats, facets,
      hasSearched, vehicleScope, bodyTypes, bodyTypeSearch, showBodyTypeDropdown,
      showAdvancedFilters, dbBodyTypes, globalSearchQuery, featureSearchQuery,
      priceMin, priceMax, priceMonths, priceMileage, priceDepositPct, priceMarginPct
    },
    actions: {
      setCatalog, setLoading, setSearching, setResults, setTotalCount, setActiveFilters, setExpandedCats, setFacets,
      setHasSearched, setVehicleScope, setBodyTypes, setBodyTypeSearch, setShowBodyTypeDropdown,
      setShowAdvancedFilters, setDbBodyTypes, setGlobalSearchQuery, setFeatureSearchQuery,
      setPriceMin, setPriceMax, setPriceMonths, setPriceMileage, setPriceDepositPct, setPriceMarginPct,
      setFeatureFilter, runSearch, clearFilters, handleExtractionSuccess, loadFilterState
    }
  };
}
