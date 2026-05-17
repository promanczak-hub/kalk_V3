import React, { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import type { ScoredVehicle } from '../../types';
import { computeVFM } from '../../utils/computeVFM';

export type AxisMode = 'monthly_total' | 'base_price_net' | 'monthly_amortization';

const SEGMENT_COLORS = [
  '#0ea5e9', // sky
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
  '#64748b', // slate (fallback)
];

interface ScatterPoint {
  vehicle_id: string;
  brand: string;
  model: string;
  x: number | null;
  y: number;
  vehicle_class: string;
  vfm: number | null;
  base_price_net: number | null;
  monthly_total: number | null;
  wr_pct: number | null;
  is_pinned: boolean;
  has_data: boolean;
  z: number; // size emphasis for pinned points
}

interface ComparisonScatterProps {
  results: ScoredVehicle[];
  pinnedIds: Set<string>;
  onTogglePin: (vehicleId: string) => void;
  xAxisMode: AxisMode;
  logScale: boolean;
}

const X_AXIS_LABELS: Record<AxisMode, string> = {
  monthly_total: 'TCO/mc (PLN netto)',
  base_price_net: 'Cena katalogowa (PLN netto)',
  monthly_amortization: 'Amortyzacja/mc (PLN netto)',
};

const fmtPln = (v: number | null | undefined): string => {
  if (v == null) return '—';
  return Math.round(v).toLocaleString('pl-PL') + ' PLN';
};

const fmtPct = (v: number | null | undefined): string => {
  if (v == null) return '—';
  return `${v.toFixed(0)}%`;
};

const SEGMENT_COLOR_CACHE = new Map<string, string>();
const colorForSegment = (segment: string): string => {
  if (!segment || segment === 'N/A') return SEGMENT_COLORS[SEGMENT_COLORS.length - 1];
  const cached = SEGMENT_COLOR_CACHE.get(segment);
  if (cached) return cached;
  const idx = SEGMENT_COLOR_CACHE.size % (SEGMENT_COLORS.length - 1);
  const color = SEGMENT_COLORS[idx];
  SEGMENT_COLOR_CACHE.set(segment, color);
  return color;
};

const getX = (car: ScoredVehicle, mode: AxisMode): number | null => {
  const snap = car.default_snapshot;
  if (mode === 'base_price_net') return car.base_price_net ?? snap?.base_price_net ?? null;
  if (mode === 'monthly_total') return snap?.monthly_total ?? car.best_monthly_price ?? car.base_price_net ?? null;
  if (mode === 'monthly_amortization') return snap?.monthly_amortization ?? null;
  return null;
};

const CustomTooltip: React.FC<{ active?: boolean; payload?: Array<{ payload: ScatterPoint }> }> = ({
  active,
  payload,
}) => {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="bg-white border border-slate-300 rounded-md shadow-lg px-3 py-2 text-xs">
      <div className="font-semibold text-slate-800">
        {p.brand} {p.model}
      </div>
      <div className="text-slate-600">{p.vehicle_class}</div>
      <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5">
        <span className="text-slate-500">Dopasowanie</span>
        <span className="font-mono tabular-nums">{fmtPct(p.y)}</span>
        <span className="text-slate-500">Cena katalogu</span>
        <span className="font-mono tabular-nums">{fmtPln(p.base_price_net)}</span>
        <span className="text-slate-500">TCO/mc</span>
        <span className="font-mono tabular-nums">{fmtPln(p.monthly_total)}</span>
        <span className="text-slate-500">WR%</span>
        <span className="font-mono tabular-nums">{fmtPct(p.wr_pct)}</span>
        <span className="text-slate-500">VFM</span>
        <span className="font-mono tabular-nums">{p.vfm != null ? p.vfm.toFixed(2) : '—'}</span>
      </div>
      <div className="mt-1 text-[10px] text-violet-600">
        {p.is_pinned ? 'Kliknij ponownie, aby odpiąć' : 'Kliknij, aby przypiąć do porównania'}
      </div>
    </div>
  );
};

export const ComparisonScatter: React.FC<ComparisonScatterProps> = ({
  results,
  pinnedIds,
  onTogglePin,
  xAxisMode,
  logScale,
}) => {
  const { points, bySegment } = useMemo(() => {
    const out: ScatterPoint[] = [];
    for (const car of results) {
      const x = getX(car, xAxisMode);
      const y = car.match_score_pct ?? 50;
      const isPinned = pinnedIds.has(car.vehicle_id);
      const segment = car.vehicle_class ?? 'N/A';
      out.push({
        vehicle_id: car.vehicle_id,
        brand: car.brand,
        model: car.model,
        x,
        y,
        vehicle_class: segment,
        vfm: computeVFM(car.match_score_pct, car.base_price_net),
        base_price_net: car.base_price_net ?? null,
        monthly_total: car.default_snapshot?.monthly_total ?? null,
        wr_pct: car.default_snapshot?.wr_pct ?? null,
        is_pinned: isPinned,
        has_data: x != null,
        z: isPinned ? 220 : 90,
      });
    }
    const bySeg = new Map<string, ScatterPoint[]>();
    for (const p of out) {
      const key = p.vehicle_class || 'N/A';
      const list = bySeg.get(key);
      if (list) list.push(p);
      else bySeg.set(key, [p]);
    }
    return { points: out, bySegment: bySeg };
  }, [results, pinnedIds, xAxisMode]);

  const xDomain = useMemo<[number | 'auto', number | 'auto']>(() => {
    const xs = points.map((p) => p.x).filter((v): v is number => v != null && v > 0);
    if (xs.length === 0) return ['auto', 'auto'];
    const min = Math.min(...xs);
    const max = Math.max(...xs);
    return [Math.floor(min * 0.95), Math.ceil(max * 1.05)];
  }, [points]);

  if (points.length === 0) {
    return <div className="p-8 text-center text-slate-500 text-sm">Brak wyników do pokazania.</div>;
  }

  return (
    <div className="w-full h-[480px]">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 24, bottom: 32, left: 32 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            type="number"
            dataKey="x"
            name="X"
            domain={xDomain}
            scale={logScale ? 'log' : 'linear'}
            allowDataOverflow
            tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
            label={{ value: X_AXIS_LABELS[xAxisMode], position: 'insideBottom', offset: -18, fontSize: 12 }}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Dopasowanie"
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
            label={{ value: 'Dopasowanie %', angle: -90, position: 'insideLeft', fontSize: 12 }}
            tick={{ fontSize: 11 }}
          />
          <ZAxis type="number" dataKey="z" range={[60, 260]} />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            align="right"
            wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
            iconType="circle"
          />
          {Array.from(bySegment.entries()).map(([segment, segPoints]) => (
            <Scatter
              key={segment}
              name={segment}
              data={segPoints}
              fill={colorForSegment(segment)}
              fillOpacity={0.85}
              stroke={colorForSegment(segment)}
              onClick={(payload: { vehicle_id?: string } | undefined) => {
                if (payload?.vehicle_id) onTogglePin(payload.vehicle_id);
              }}
              cursor="pointer"
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
};
