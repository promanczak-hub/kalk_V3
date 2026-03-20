import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import type { SelectedFeature, SearchContext, ScoredVehicle } from '../types';
import { buildScoringPayload } from '../utils/buildScoringPayload';
import { apiClient } from "../../lib/apiClient";

export const useScoringSearch = () => {
  const [searchContext, setSearchContext] = useState<SearchContext>({
    brands: [],
    models: [],
    trims: [],
    samarClassIds: [],
    bodyTypes: [],
    useMatrixFilters: false,
    duration_months_range: [24, 48],
    total_mileage_range: [60000, 140000],
    exact_mode: true,
    exact_duration_months: 48,
    exact_total_mileage: 80000,
    margin_pct: 10,
    monthly_budget: undefined,
  });
  
  const [selectedFeatures, setSelectedFeatures] = useState<SelectedFeature[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<ScoredVehicle[]>([]);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  const handleSearch = useCallback(async () => {
    setIsSearching(true);

    // Abort previous ongoing request to prevent race conditions
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      // Build requirements payload out of selectedFeatures and context
      const payload = buildScoringPayload(searchContext, selectedFeatures);

      const { apiFetch } = await import('../../lib/api');
      const res = await apiClient.fetch('/api/scoring-search/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal
      });
      
      if (res.ok) {
        const data = await res.json();
        if (!signal.aborted) {
          setSearchResults(data.results || []);
        }
      } else {
        const errText = await res.text();
        if (!signal.aborted) {
          console.error('Search error', errText);
          setSearchResults([]);
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Search request aborted due to a newer request.');
      } else {
        console.error(err);
        if (!signal.aborted) {
          setSearchResults([]);
        }
      }
    } finally {
      if (!signal.aborted) {
        setIsSearching(false);
      }
    }
  }, [searchContext, selectedFeatures]);

  // ── Auto-search with debounce on every filter change ──
  const searchKey = useMemo(
    () => JSON.stringify({ searchContext, selectedFeatures }),
    [searchContext, selectedFeatures]
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      handleSearch();
    }, 600);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchKey]);

  return {
    searchContext,
    setSearchContext,
    selectedFeatures,
    setSelectedFeatures,
    searchResults,
    isSearching,
    snackbarMessage,
    setSnackbarMessage,
    handleSearch
  };
};
