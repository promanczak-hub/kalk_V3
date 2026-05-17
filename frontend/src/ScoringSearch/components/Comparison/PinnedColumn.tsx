import React, { useState } from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { X, ChevronDown, ChevronUp } from 'lucide-react';
import type { ScoredVehicle, VehicleSnapshot } from '../../types';
import { computeVFM, formatVFM } from '../../utils/computeVFM';

interface PinnedColumnProps {
  car: ScoredVehicle;
  snapshot: VehicleSnapshot | null | undefined;
  loading: boolean;
  onClose: () => void;
  onRequestCurve: () => void;
}

const fmtPln = (v: number | null | undefined): string => {
  if (v == null) return '—';
  return Math.round(v).toLocaleString('pl-PL');
};
const fmtPct = (v: number | null | undefined): string => (v == null ? '—' : `${v.toFixed(0)}%`);

const ROW_CLS = 'flex items-baseline justify-between gap-2 py-0.5 text-[12px]';
const LABEL_CLS = 'text-slate-500';
const VAL_CLS = 'font-mono tabular-nums text-slate-800';
const VAL_MUTED = 'font-mono tabular-nums text-slate-400';

export const PinnedColumn: React.FC<PinnedColumnProps> = ({
  car,
  snapshot,
  loading,
  onClose,
  onRequestCurve,
}) => {
  const [curveOpen, setCurveOpen] = useState(false);

  const hasData = snapshot && snapshot.found && snapshot.error !== 'not_in_cache';
  const isNullDecomp = snapshot?.error === 'null_decomposition';
  const isSnapped = snapshot?.error === 'snap_to_nearest';
  const vfm = computeVFM(car.match_score_pct, car.base_price_net);

  const toggleCurve = () => {
    const next = !curveOpen;
    setCurveOpen(next);
    if (next && (!snapshot?.wr_curve || snapshot.wr_curve.length === 0)) {
      onRequestCurve();
    }
  };

  return (
    <div className="flex-shrink-0 w-[220px] border border-slate-200 rounded-lg bg-white shadow-sm flex flex-col">
      <div className="flex items-start justify-between gap-2 p-2 border-b border-slate-100">
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-semibold text-slate-800 truncate">
            {car.brand} {car.model}
          </div>
          <div className="text-[11px] text-slate-500 truncate">{car.version || car.trim_level || ''}</div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-700 transition-colors"
          aria-label="Odepnij pojazd"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex gap-1 px-2 py-1.5 border-b border-slate-100">
        <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5 text-[11px] font-mono tabular-nums">
          {fmtPct(car.match_score_pct)}
        </span>
        {vfm != null && (
          <span className="inline-flex items-center gap-1 text-violet-700 bg-violet-50 border border-violet-200 rounded-full px-2 py-0.5 text-[11px] font-mono tabular-nums">
            VFM {formatVFM(vfm)}
          </span>
        )}
      </div>

      {!hasData ? (
        <div className="px-2 py-3 text-center text-[11px] text-slate-500">
          {loading ? 'Ładowanie…' : 'Brak kalkulacji dla tych parametrów'}
        </div>
      ) : (
        <div className="p-2 space-y-0.5">
          {isSnapped && (
            <div className="mb-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
              Wycena przybliżona ({snapshot?.duration_months} mc)
            </div>
          )}
          {isNullDecomp && (
            <div className="mb-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
              Dekompozycja w trakcie odświeżania
            </div>
          )}
          <div className={ROW_CLS}>
            <span className={LABEL_CLS}>WR</span>
            <span className={isNullDecomp ? VAL_MUTED : VAL_CLS}>
              {fmtPct(snapshot?.wr_pct)} · {fmtPln(snapshot?.wr_pln)} zł
            </span>
          </div>
          <div className={ROW_CLS}>
            <span className={LABEL_CLS}>Amortyzacja/mc</span>
            <span className={isNullDecomp ? VAL_MUTED : VAL_CLS}>{fmtPln(snapshot?.monthly_amortization)}</span>
          </div>
          <div className={ROW_CLS}>
            <span className={LABEL_CLS}>Serwis/mc</span>
            <span className={isNullDecomp ? VAL_MUTED : VAL_CLS}>{fmtPln(snapshot?.monthly_service)}</span>
          </div>
          <div className={ROW_CLS}>
            <span className={LABEL_CLS}>Opony/mc</span>
            <span className={isNullDecomp ? VAL_MUTED : VAL_CLS}>{fmtPln(snapshot?.monthly_tires)}</span>
          </div>
          <div className={ROW_CLS}>
            <span className={LABEL_CLS}>Ubezpieczenie/mc</span>
            <span className={isNullDecomp ? VAL_MUTED : VAL_CLS}>{fmtPln(snapshot?.monthly_insurance)}</span>
          </div>
          <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-baseline justify-between">
            <span className="text-[11px] uppercase tracking-wider text-slate-600 font-semibold">TCO/mc</span>
            <span className="font-mono tabular-nums text-[14px] font-semibold text-slate-900">
              {fmtPln(snapshot?.monthly_total)}
            </span>
          </div>

          <button
            onClick={toggleCurve}
            className="mt-1 w-full inline-flex items-center justify-between gap-1 text-[11px] text-violet-700 hover:bg-violet-50 rounded px-1.5 py-1 transition-colors"
          >
            <span>{curveOpen ? 'Ukryj krzywą WR' : 'Rozwiń krzywą WR'}</span>
            {curveOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {curveOpen && (
            <div className="mt-1 h-[100px]">
              {snapshot?.wr_curve && snapshot.wr_curve.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={snapshot.wr_curve.map((p) => ({
                      duration_months: p.duration_months,
                      wr_pct: p.wr_pct ?? null,
                      tco: p.monthly_total ?? null,
                    }))}
                    margin={{ top: 4, right: 8, bottom: 0, left: -10 }}
                  >
                    <XAxis dataKey="duration_months" tick={{ fontSize: 9 }} interval={0} />
                    <YAxis tick={{ fontSize: 9 }} width={30} />
                    <Tooltip
                      formatter={(v: number, name: string) => [
                        name === 'wr_pct' ? `${Math.round(v)}%` : `${Math.round(v).toLocaleString('pl-PL')} PLN`,
                        name === 'wr_pct' ? 'WR' : 'TCO/mc',
                      ]}
                      labelFormatter={(l) => `${l} mc`}
                    />
                    <Line type="monotone" dataKey="wr_pct" stroke="#8b5cf6" dot={{ r: 2 }} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              ) : loading ? (
                <div className="text-[10px] text-slate-400 text-center pt-8">Ładowanie krzywej…</div>
              ) : (
                <div className="text-[10px] text-slate-400 text-center pt-8">Brak danych krzywej</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
