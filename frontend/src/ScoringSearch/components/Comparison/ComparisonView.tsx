import React, { useCallback, useEffect, useMemo, useState } from 'react';
import type { ScoredVehicle, VehicleSnapshot } from '../../types';
import { useComparisonSnapshot } from '../../hooks/useComparisonSnapshot';
import { ComparisonScatter, type AxisMode } from './ComparisonScatter';
import { PinnedPanel } from './PinnedPanel';
import { apiClient } from '../../../lib/apiClient';

interface ComparisonViewProps {
  results: ScoredVehicle[];
}

const STORAGE_KEY = 'kalk_v3:compare:snapshot_params';
const MAX_PINNED = 8;
const DURATIONS = [24, 36, 48, 60] as const;
const MILEAGES = [10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 80000, 100000] as const;

const AXIS_OPTIONS: { value: AxisMode; label: string }[] = [
  { value: 'monthly_total', label: 'TCO/mc' },
  { value: 'base_price_net', label: 'Cena katalogowa' },
  { value: 'monthly_amortization', label: 'Amortyzacja/mc' },
];

interface Persisted {
  months?: number;
  annual_mileage?: number;
  xAxis?: AxisMode;
  logScale?: boolean;
}

const loadPersisted = (): Persisted => {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Persisted) : {};
  } catch {
    return {};
  }
};

const savePersisted = (state: Persisted): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Silent — quota or private mode; persistence is a nice-to-have here.
  }
};

export const ComparisonView: React.FC<ComparisonViewProps> = ({ results }) => {
  const persisted = useMemo(loadPersisted, []);
  const [months, setMonths] = useState<number>(persisted.months ?? 36);
  const [annualMileage, setAnnualMileage] = useState<number>(persisted.annual_mileage ?? 30000);
  const [xAxisMode, setXAxisMode] = useState<AxisMode>(persisted.xAxis ?? 'monthly_total');
  const [logScale, setLogScale] = useState<boolean>(persisted.logScale ?? false);
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const [curveOverrides, setCurveOverrides] = useState<Record<string, VehicleSnapshot>>({});

  useEffect(() => {
    savePersisted({ months, annual_mileage: annualMileage, xAxis: xAxisMode, logScale });
  }, [months, annualMileage, xAxisMode, logScale]);

  useEffect(() => {
    if (!snackbar) return;
    const t = setTimeout(() => setSnackbar(null), 2500);
    return () => clearTimeout(t);
  }, [snackbar]);

  // Re-fetch decomposition for all results when (months, mileage) deviate from
  // the default-snapshot baked into the search response. When they match the
  // defaults we just use the in-row default_snapshot — no network roundtrip.
  const needsRefetch = months !== 36 || annualMileage !== 30000;
  const allIds = useMemo(() => results.map((r) => r.vehicle_id), [results]);
  const { snapshots: liveSnapshots, loading: snapshotsLoading } = useComparisonSnapshot(
    needsRefetch ? allIds : [],
    months,
    annualMileage,
    false,
  );

  // Merge live snapshots over the default_snapshot from the search response so
  // the scatter X-axis stays accurate for whatever (mc, km) the user picked.
  const resultsWithSnapshot = useMemo<ScoredVehicle[]>(() => {
    if (!needsRefetch) return results;
    return results.map((car) => {
      const fresh = liveSnapshots[car.vehicle_id];
      if (!fresh) return car;
      return { ...car, default_snapshot: fresh };
    });
  }, [results, needsRefetch, liveSnapshots]);

  const pinnedCars = useMemo(
    () => resultsWithSnapshot.filter((c) => pinnedIds.has(c.vehicle_id)),
    [resultsWithSnapshot, pinnedIds],
  );
  const pinnedIdsArr = useMemo(() => Array.from(pinnedIds), [pinnedIds]);
  const { snapshots: pinnedSnapshots, loading: pinnedLoading } = useComparisonSnapshot(
    pinnedIdsArr,
    months,
    annualMileage,
    false,
  );

  const togglePin = useCallback(
    (vid: string) => {
      setPinnedIds((prev) => {
        const next = new Set(prev);
        if (next.has(vid)) {
          next.delete(vid);
        } else {
          if (next.size >= MAX_PINNED) {
            setSnackbar(`Maks. ${MAX_PINNED} pojazdów do porównania`);
            return prev;
          }
          next.add(vid);
        }
        return next;
      });
    },
    [],
  );

  const clearAll = useCallback(() => setPinnedIds(new Set()), []);

  const requestCurve = useCallback(
    async (vid: string) => {
      try {
        const res = await apiClient.fetch('/api/scoring-search/comparison-snapshot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vehicle_ids: [vid],
            months,
            annual_mileage: annualMileage,
            include_curve: true,
          }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as { snapshots: Record<string, VehicleSnapshot> };
        const snap = data.snapshots?.[vid];
        if (snap) {
          setCurveOverrides((prev) => ({ ...prev, [vid]: snap }));
        }
      } catch {
        // Silent — column will show "Brak danych krzywej".
      }
    },
    [months, annualMileage],
  );

  const mergedSnapshots = useMemo<Record<string, VehicleSnapshot>>(() => {
    const out: Record<string, VehicleSnapshot> = {};
    for (const vid of pinnedIdsArr) {
      out[vid] = curveOverrides[vid] ?? pinnedSnapshots[vid] ?? resultsWithSnapshot.find((c) => c.vehicle_id === vid)?.default_snapshot ?? {
        vehicle_id: vid,
        found: false,
        error: 'not_in_cache',
      };
    }
    return out;
  }, [pinnedIdsArr, curveOverrides, pinnedSnapshots, resultsWithSnapshot]);

  return (
    <div className="border border-slate-200 rounded-lg bg-white overflow-hidden">
      {/* Toolbar */}
      <div className="sticky top-0 z-10 flex flex-wrap items-center gap-3 px-3 py-2 bg-white border-b border-slate-200 text-[12px]">
        <label className="inline-flex items-center gap-1.5">
          <span className="text-slate-500">Okres</span>
          <select
            className="border border-slate-300 rounded px-1.5 py-0.5 bg-white text-slate-800"
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
          >
            {DURATIONS.map((m) => (
              <option key={m} value={m}>
                {m} mc
              </option>
            ))}
          </select>
        </label>
        <label className="inline-flex items-center gap-1.5">
          <span className="text-slate-500">Przebieg roczny</span>
          <select
            className="border border-slate-300 rounded px-1.5 py-0.5 bg-white text-slate-800"
            value={annualMileage}
            onChange={(e) => setAnnualMileage(Number(e.target.value))}
          >
            {MILEAGES.map((km) => (
              <option key={km} value={km}>
                {(km / 1000).toFixed(0)}k km
              </option>
            ))}
          </select>
        </label>
        <label className="inline-flex items-center gap-1.5">
          <span className="text-slate-500">Oś X</span>
          <select
            className="border border-slate-300 rounded px-1.5 py-0.5 bg-white text-slate-800"
            value={xAxisMode}
            onChange={(e) => setXAxisMode(e.target.value as AxisMode)}
          >
            {AXIS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-flex items-center gap-1.5">
          <input type="checkbox" checked={logScale} onChange={(e) => setLogScale(e.target.checked)} />
          <span className="text-slate-700">Skala log</span>
        </label>
        <div className="flex-1" />
        <span className="text-[11px] text-slate-500">
          Pinned: {pinnedIds.size}/{MAX_PINNED}
          {snapshotsLoading || pinnedLoading ? ' · ładowanie…' : ''}
        </span>
      </div>

      <ComparisonScatter
        results={resultsWithSnapshot}
        pinnedIds={pinnedIds}
        onTogglePin={togglePin}
        xAxisMode={xAxisMode}
        logScale={logScale}
      />

      <PinnedPanel
        pinnedCars={pinnedCars}
        snapshots={mergedSnapshots}
        loading={pinnedLoading}
        onUnpin={togglePin}
        onClearAll={clearAll}
        onRequestCurve={requestCurve}
      />

      {snackbar && (
        <div className="fixed bottom-4 right-4 bg-slate-900 text-white text-[12px] px-3 py-2 rounded-md shadow-lg z-50">
          {snackbar}
        </div>
      )}
    </div>
  );
};
