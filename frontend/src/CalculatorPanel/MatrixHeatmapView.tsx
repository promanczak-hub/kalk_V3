import { useMemo, useState } from "react";
import { Star, Grid3X3, List } from "lucide-react";

/* ── Types ───────────────────────────────────────────────────────────── */

interface MatrixCell {
  months: number;
  km_per_year: number;
  total_km: number;
  base_cost_net: number;
  price_net: number;
  status: string;
  breakdown: {
    finance: { base: number; margin: number; price: number };
    technical: {
      service: { base: number; margin: number; price: number };
      tires: { base: number; margin: number; price: number };
      insurance: { base: number; margin: number; price: number };
      replacement_car: { base: number; margin: number; price: number };
      additional_costs: { base: number; margin: number; price: number };
    };
  };
}

interface MatrixHeatmapViewProps {
  cells: MatrixCell[];
  onCellClick?: (cell: MatrixCell) => void;
}

/* ── Margin Tier System ─────────────────────────────────────────────── */

interface MarginTier {
  label: string;
  heatBg: string;
  heatColor: string;
  badgeBg: string;
  badgeText: string;
}

function getMarginTier(pct: number): MarginTier {
  if (pct < 0) return {
    label: "< 0%", heatBg: "#ffffff", heatColor: "#dc2626",
    badgeBg: "bg-red-50", badgeText: "text-red-700"
  };
  if (pct < 8) return {
    label: "0–8%", heatBg: "#ffffff", heatColor: "#ea580c",
    badgeBg: "bg-orange-50", badgeText: "text-orange-700"
  };
  if (pct < 12) return {
    label: "8–12%", heatBg: "#ffffff", heatColor: "#ca8a04",
    badgeBg: "bg-yellow-50", badgeText: "text-yellow-700"
  };
  if (pct < 15) return {
    label: "12–15%", heatBg: "#ffffff", heatColor: "#16a34a",
    badgeBg: "bg-green-50", badgeText: "text-green-700"
  };
  if (pct < 20) return {
    label: "15–20%", heatBg: "#ffffff", heatColor: "#059669",
    badgeBg: "bg-emerald-50", badgeText: "text-emerald-700"
  };
  return {
    label: "> 20%", heatBg: "#ffffff", heatColor: "#0891b2",
    badgeBg: "bg-cyan-50", badgeText: "text-cyan-700"
  };
}

function fmtPLN(v: number): string {
  return v.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/* ── Legend tiers ──────────────────────────────────────────────────── */

const LEGEND_TIERS = [
  { pct: -1, label: "< 0%" },
  { pct: 4, label: "0–8%" },
  { pct: 10, label: "8–12%" },
  { pct: 13, label: "12–15%" },
  { pct: 17, label: "15–20%" },
  { pct: 25, label: "> 20%" },
];

/* ── Main Component ────────────────────────────────────────────────── */

export function MatrixHeatmapView({ cells, onCellClick }: MatrixHeatmapViewProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  // Build axes from actual cell data
  const { months, kmValues, cellMap, bestKey } = useMemo(() => {
    const monthsSet = new Set<number>();
    const kmSet = new Set<number>();
    const map = new Map<string, MatrixCell>();

    for (const c of cells) {
      monthsSet.add(c.months);
      kmSet.add(c.km_per_year);
      map.set(`${c.months}_${c.km_per_year}`, c);
    }

    const sortedMonths = [...monthsSet].sort((a, b) => a - b);
    const sortedKm = [...kmSet].sort((a, b) => a - b);

    // Find best cell (highest margin)
    let best: MatrixCell | null = null;
    let bestMargin = -Infinity;
    for (const c of cells) {
      const m = c.base_cost_net > 0 ? ((c.price_net - c.base_cost_net) / c.price_net) * 100 : 0;
      if (m > bestMargin) {
        bestMargin = m;
        best = c;
      }
    }
    const bk = best ? `${best.months}_${best.km_per_year}` : null;

    return { months: sortedMonths, kmValues: sortedKm, cellMap: map, bestKey: bk };
  }, [cells]);

  if (cells.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-slate-400">
        Brak danych do wyświetlenia
      </div>
    );
  }

  return (
    <div>
      {/* Matrix table */}
      <div className="overflow-x-auto border border-slate-200 bg-white">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {/* Corner cell */}
              <th className="py-2.5 px-3 text-left w-24">
                <div className="text-[9px] font-bold uppercase text-slate-400 tracking-wider">
                  Okres ↓ / km →
                </div>
              </th>
              {kmValues.map((km) => (
                <th key={km} className="py-2.5 text-center">
                  <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                    {(km / 1000).toFixed(0)}k
                  </div>
                  <div className="text-[8px] text-slate-300 font-medium">km/rok</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {months.map((m) => (
              <tr key={m}>
                {/* Row header */}
                <td className="py-2 px-3 border-b border-r border-slate-100 align-middle">
                  <div className="text-xs font-bold text-slate-600">{m} mc</div>
                  <div className="text-[9px] text-slate-400">
                    {m === 12 ? "1 rok" : m === 24 ? "2 lata" : m === 36 ? "3 lata" : m === 48 ? "4 lata" : m === 60 ? "5 lat" : m === 72 ? "6 lat" : m === 84 ? "7 lat" : `${(m / 12).toFixed(1)} lat`}
                  </div>
                </td>

                {/* Data cells */}
                {kmValues.map((km) => {
                  const key = `${m}_${km}`;
                  const cell = cellMap.get(key);

                  if (!cell) {
                    return (
                      <td key={km} className="text-center p-2 border-b border-slate-100">
                        <div className="p-3 bg-slate-50 border border-dashed border-slate-200">
                          <span className="text-xs text-slate-300">—</span>
                        </div>
                      </td>
                    );
                  }

                  const marginPct = cell.base_cost_net > 0
                    ? ((cell.price_net - cell.base_cost_net) / cell.price_net) * 100
                    : 0;
                  const tier = getMarginTier(marginPct);
                  const isSelected = selectedKey === key;
                  const isBest = bestKey === key;
                  const totalKmK = (cell.total_km / 1000).toFixed(0);

                  return (
                    <td key={km} className="text-center p-2 border-b border-slate-100">
                      <button
                        onClick={() => {
                          setSelectedKey(isSelected ? null : key);
                          if (onCellClick && !isSelected) onCellClick(cell);
                        }}
                        className={`
                          relative w-full rounded-sm p-3 transition-all duration-150
                          cursor-pointer group min-w-[100px] bg-white
                          ${isSelected
                            ? "ring-1 ring-offset-0 shadow-sm"
                            : "hover:shadow-sm"
                          }
                        `}
                        style={{
                          borderWidth: "1px",
                          borderStyle: "solid",
                          borderColor: isSelected ? tier.heatColor : `${tier.heatColor}60`,
                          boxShadow: isSelected ? `0 0 0 1px ${tier.heatColor}` : undefined
                        }}
                      >
                        {/* Best cell star */}
                        {isBest && (
                          <div className="absolute top-1 right-1 z-10">
                            <Star className="w-3 h-3" style={{ color: tier.heatColor, fill: tier.heatColor }} />
                          </div>
                        )}

                        {/* Price */}
                        <div className="text-[13px] font-bold tabular-nums leading-tight text-slate-800">
                          {fmtPLN(cell.price_net)}
                        </div>

                        {/* Total km */}
                        <div className="text-[9px] text-slate-500 mt-1">
                          {totalKmK}k km
                        </div>

                        {/* Margin badge */}
                        <div className="mt-1.5">
                          <span
                            className={`inline-block text-[9px] font-semibold px-1.5 py-0.5 rounded-sm ${tier.badgeBg} ${tier.badgeText}`}
                          >
                            {marginPct.toFixed(1)}%
                          </span>
                        </div>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3 ml-1">
        <span className="text-[9px] text-slate-400 font-semibold mr-1 uppercase">Marża:</span>
        {LEGEND_TIERS.map((t) => {
          const tier = getMarginTier(t.pct);
          return (
            <span
              key={t.label}
              className={`text-[9px] font-semibold px-2 py-0.5 rounded-sm ${tier.badgeBg} ${tier.badgeText}`}
            >
              {t.label}
            </span>
          );
        })}
      </div>

      {/* Selected cell detail */}
      {selectedKey && (() => {
        const cell = cellMap.get(selectedKey);
        if (!cell) return null;
        const marginPct = cell.base_cost_net > 0
          ? ((cell.price_net - cell.base_cost_net) / cell.price_net) * 100
          : 0;
        const tier = getMarginTier(marginPct);

        return (
          <div
            className="mt-3 p-4 rounded-sm border shadow-sm animate-in fade-in slide-in-from-top-2 duration-200 bg-white"
            style={{ borderColor: tier.heatColor }}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${tier.badgeBg} ${tier.badgeText}`}
                >
                  {cell.months} mc / {(cell.km_per_year / 1000).toFixed(0)}k km/rok
                </span>
                <span className="text-[10px] text-slate-400">
                  ({(cell.total_km / 1000).toFixed(0)}k km łącznie)
                </span>
              </div>
              <button
                onClick={() => setSelectedKey(null)}
                className="text-[10px] text-slate-400 hover:text-slate-600 transition-colors"
              >
                ✕ Zamknij
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <DetailItem label="Rata netto/mc" value={`${fmtPLN(cell.price_net)} PLN`} highlight />
              <DetailItem label="Koszt bazowy" value={`${fmtPLN(cell.base_cost_net)} PLN`} />
              <DetailItem label="Marża %"
                value={`${marginPct.toFixed(1)}%`}
                color={tier.heatColor}
              />
              <DetailItem label="Marża PLN/mc"
                value={`${fmtPLN(cell.price_net - cell.base_cost_net)} PLN`}
              />
            </div>

            {/* Breakdown */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 pt-3 border-t border-slate-200/60">
              <BreakdownItem label="Finanse" value={cell.breakdown.finance.price} />
              <BreakdownItem label="Serwis" value={cell.breakdown.technical.service.price} />
              <BreakdownItem label="Opony" value={cell.breakdown.technical.tires.price} />
              <BreakdownItem label="Ubezp." value={cell.breakdown.technical.insurance.price} />
              <BreakdownItem label="Inne" value={
                cell.breakdown.technical.replacement_car.price +
                cell.breakdown.technical.additional_costs.price
              } />
            </div>
          </div>
        );
      })()}
    </div>
  );
}

/* ── Sub-components ─────────────────────────────────────────────────── */

function DetailItem({ label, value, highlight, color }: {
  label: string; value: string; highlight?: boolean; color?: string;
}) {
  return (
    <div>
      <div className="text-[9px] font-bold uppercase text-slate-400 tracking-wider">{label}</div>
      <div
        className={`text-sm font-bold tabular-nums ${highlight ? "text-blue-700" : ""}`}
        style={color ? { color } : undefined}
      >
        {value}
      </div>
    </div>
  );
}

function BreakdownItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center p-1.5 rounded-lg bg-white/60">
      <div className="text-[8px] font-bold uppercase text-slate-400 tracking-wider">{label}</div>
      <div className="text-[11px] font-bold text-slate-700 tabular-nums">{fmtPLN(value)}</div>
    </div>
  );
}

/* ── View Toggle Button ────────────────────────────────────────────── */

export function MatrixViewToggle({
  view,
  onViewChange,
}: {
  view: "cards" | "heatmap";
  onViewChange: (v: "cards" | "heatmap") => void;
}) {
  return (
    <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => onViewChange("cards")}
        className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all ${
          view === "cards"
            ? "bg-blue-600 text-white shadow-inner"
            : "text-slate-400 hover:bg-slate-50"
        }`}
      >
        <List className="w-3 h-3" />
        Karty
      </button>
      <button
        onClick={() => onViewChange("heatmap")}
        className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all ${
          view === "heatmap"
            ? "bg-blue-600 text-white shadow-inner"
            : "text-slate-400 hover:bg-slate-50"
        }`}
      >
        <Grid3X3 className="w-3 h-3" />
        Matryca
      </button>
    </div>
  );
}
