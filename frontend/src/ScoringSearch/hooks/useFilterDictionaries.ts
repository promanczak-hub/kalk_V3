import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '../../lib/apiClient';
import type {
  AvailableFiltersResponse, SearchContext, EnumFilter, InitialDataResponse,
  TrimsAndOptionsResponse, BooleanFilter
} from '../types';

interface UseFilterDictionariesProps {
  searchContext: SearchContext;
  onLevel2: boolean;
}

export const useFilterDictionaries = ({ searchContext, onLevel2 }: UseFilterDictionariesProps) => {
  const [loadingInitial, setLoadingInitial] = useState(false);
  const [initialData, setInitialData] = useState<InitialDataResponse | null>(null);
  
  const [loadingFilters, setLoadingFilters] = useState(false);
  const [data, setData] = useState<AvailableFiltersResponse | null>(null);
  
  const [trimsAndOptions, setTrimsAndOptions] = useState<TrimsAndOptionsResponse | null>(null);
  const [loadingTrims, setLoadingTrims] = useState(false);

  // 1. Fetch initial basic dictionaries (brands, body types) once
  useEffect(() => {
    const fetchInitialData = async () => {
      setLoadingInitial(true);
      try {
        const res = await apiClient.fetch('/api/scoring-search/initial-data', { method: 'GET' });
        if (res.ok) {
          const json = await res.json();
          setInitialData(json.data || json);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingInitial(false);
      }
    };
    fetchInitialData();
  }, []);

  // 2. Fetch specific available filters and trims based on criteria or view (level 2 focus)
  useEffect(() => {
    const hasBrandOrModelOrBody = searchContext.brands.length > 0 || searchContext.models.length > 0 || searchContext.bodyTypes.length > 0;
    if (hasBrandOrModelOrBody || onLevel2) {
      
      const fetchFilters = async () => {
        setLoadingFilters(true);
        try {
          const payload = {
            brands: searchContext.brands.length > 0 ? searchContext.brands : null,
            models: searchContext.models.length > 0 ? searchContext.models : null,
            body_types: searchContext.bodyTypes.length > 0 ? searchContext.bodyTypes : null,
            samar_class_ids: null,
          };
          const res = await apiClient.fetch('/api/scoring-search/available-filters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          if (res.ok) {
            const json = await res.json();
            setData(json.data || json);
          }
        } catch (err) {
          console.error(err);
        } finally {
          setLoadingFilters(false);
        }
      };

      const fetchTrimsAndOptions = async () => {
        // RPC rpc_get_trims_and_options accepts NULL/NULL and returns the full
        // catalog of equipment across all completed vehicles. The previous
        // brand+model gate left users staring at "Wybierz model…" even though
        // the dataset was searchable globally.
        setLoadingTrims(true);
        try {
          const payload = {
            brands: searchContext.brands.length > 0 ? searchContext.brands : null,
            models: searchContext.models.length > 0 ? searchContext.models : null,
          };
          const res = await apiClient.fetch('/api/scoring-search/trims-and-options', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          if (res.ok) {
            const json: TrimsAndOptionsResponse = await res.json();
            setTrimsAndOptions(json);
          }
        } catch (err) {
          console.error(err);
        } finally {
          setLoadingTrims(false);
        }
      };

      fetchFilters();
      fetchTrimsAndOptions();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchContext.brands.length, searchContext.models.length, searchContext.bodyTypes.length, onLevel2]);

  // ── Derived Data / Memos ──

  // Brands sorted by count descending
  const sortedBrands = useMemo(() => {
    if (!initialData?.brands) return [];
    const counts = initialData.brand_counts || {};
    return [...initialData.brands].sort((a, b) => (counts[b] || 0) - (counts[a] || 0));
  }, [initialData]);

  // Primary enum facets
  const primaryEnumFacets = useMemo(() => {
    if (!data?.facet_groups) return [];
    const facets: EnumFilter[] = [];
    for (const group of data.facet_groups) {
      for (const filter of group.filters) {
        if (filter.items && filter.items.length > 0 && filter.key !== 'body_style') facets.push(filter);
      }
    }
    return facets;
  }, [data]);

  // Boolean filter groups — sorted by total count desc
  const sortedBooleanGroups = useMemo(() => {
    if (!data?.boolean_filters) return [];
    const groups = Array.from(new Set(data.boolean_filters.map((f: BooleanFilter) => f.group_name)));
    return groups
      .map((groupName: string) => ({
        groupName,
        filters: data.boolean_filters!
          .filter((f: BooleanFilter) => f.group_name === groupName)
          .sort((a: BooleanFilter, b: BooleanFilter) => (b.cnt ?? 0) - (a.cnt ?? 0)),
        totalCount: data.boolean_filters!
          .filter((f: BooleanFilter) => f.group_name === groupName)
          .reduce((sum: number, f: BooleanFilter) => sum + (f.cnt ?? 0), 0),
      }))
      .sort((a, b) => b.totalCount - a.totalCount);
  }, [data]);

  return {
    initialData,
    loadingInitial,
    data,
    loadingFilters,
    trimsAndOptions,
    loadingTrims,
    sortedBrands,
    primaryEnumFacets,
    sortedBooleanGroups
  };
};
