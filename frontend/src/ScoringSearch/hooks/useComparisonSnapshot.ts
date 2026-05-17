import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../../lib/apiClient';
import type {
  ComparisonSnapshotRequest,
  ComparisonSnapshotResponse,
  VehicleSnapshot,
} from '../types';

type State = {
  snapshots: Record<string, VehicleSnapshot>;
  loading: boolean;
  error: string | null;
};

const DEBOUNCE_MS = 250;
const ENDPOINT = '/api/scoring-search/comparison-snapshot';

const cacheKey = (vid: string, m: number, km: number, curve: boolean) =>
  `${vid}|${m}|${km}|${curve ? 'c' : 'p'}`;

/**
 * Fetch the comparison-chart snapshot (WR%, koszty techniczne, TCO/mc) for a
 * set of vehicles. Debounced 250ms so picker slides don't spam the backend;
 * AbortController cancels in-flight calls when params change; an in-memory
 * cache absorbs repeat queries (e.g. picking the same params twice).
 */
export function useComparisonSnapshot(
  vehicleIds: string[],
  months: number,
  annualMileage: number,
  includeCurve: boolean = false,
): State & { refetch: () => void } {
  const [state, setState] = useState<State>({ snapshots: {}, loading: false, error: null });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const cacheRef = useRef<Map<string, VehicleSnapshot>>(new Map());

  const fetchNow = useCallback(async () => {
    if (vehicleIds.length === 0) {
      setState({ snapshots: {}, loading: false, error: null });
      return;
    }

    const hitFromCache: Record<string, VehicleSnapshot> = {};
    const toFetch: string[] = [];
    for (const vid of vehicleIds) {
      const hit = cacheRef.current.get(cacheKey(vid, months, annualMileage, includeCurve));
      if (hit) hitFromCache[vid] = hit;
      else toFetch.push(vid);
    }

    if (toFetch.length === 0) {
      setState({ snapshots: hitFromCache, loading: false, error: null });
      return;
    }

    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setState((prev) => ({ ...prev, loading: true, error: null }));

    const body: ComparisonSnapshotRequest = {
      vehicle_ids: toFetch,
      months,
      annual_mileage: annualMileage,
      include_curve: includeCurve,
    };

    try {
      const res = await apiClient.fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ac.signal,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        if (!ac.signal.aborted) {
          setState({ snapshots: hitFromCache, loading: false, error: text || 'Request failed' });
        }
        return;
      }
      const data = (await res.json()) as ComparisonSnapshotResponse;
      if (ac.signal.aborted) return;
      const merged = { ...hitFromCache };
      for (const [vid, snap] of Object.entries(data.snapshots || {})) {
        merged[vid] = snap;
        cacheRef.current.set(cacheKey(vid, months, annualMileage, includeCurve), snap);
      }
      setState({ snapshots: merged, loading: false, error: null });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      const message = err instanceof Error ? err.message : 'Unknown error';
      setState({ snapshots: hitFromCache, loading: false, error: message });
    }
  }, [vehicleIds, months, annualMileage, includeCurve]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void fetchNow();
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [fetchNow]);

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return { ...state, refetch: fetchNow };
}
