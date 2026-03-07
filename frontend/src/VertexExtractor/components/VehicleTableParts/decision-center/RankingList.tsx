import { useState, useMemo } from "react";
import { ChevronDown, ChevronUp, ArrowUpDown } from "lucide-react";
import type { MiniMatrixCell, SortCriterion } from "./decision-center.types";
import { fmtPLN, fmtPLN2, fmtKm, getMarginTier } from "./decision-center.utils";
import { CostBreakdownPanel } from "./CostBreakdownPanel";

interface RankingListProps {
  cells: MiniMatrixCell[];
  budgetMax: number | null;
}

const SORT_OPTIONS: { key: SortCriterion; label: string }[] = [
  { key: "price", label: "Cena ↑" },
  { key: "margin_pct", label: "Marża % ↓" },
  { key: "margin_value", label: "Marża PLN ↓" },
  { key: "ratio", label: "Stosunek ↓" },
];

const MEDALS = ["🥇", "🥈", "🥉"];

function sortCells(cells: MiniMatrixCell[], criterion: SortCriterion): MiniMatrixCell[] {
  const sorted = [...cells];
  switch (criterion) {
    case "price":
      return sorted.sort((a, b) => a.price_net - b.price_net);
    case "margin_pct":
      return sorted.sort((a, b) => b.marza_na_kontrakcie_pct - a.marza_na_kontrakcie_pct);
    case "margin_value":
      return sorted.sort((a, b) => b.marza_na_kontrakcie - a.marza_na_kontrakcie);
    case "ratio":
      // Ratio = margin_pct / normalized_price (higher = better deal)
      return sorted.sort((a, b) => {
        const maxPrice = Math.max(...cells.map((c) => c.price_net), 1);
        const ratioA = a.marza_na_kontrakcie_pct / (a.price_net / maxPrice);
        const ratioB = b.marza_na_kontrakcie_pct / (b.price_net / maxPrice);
        return ratioB - ratioA;
      });
    default:
      return sorted;
  }
}

export function RankingList({ cells, budgetMax }: RankingListProps) {
  const [sortBy, setSortBy] = useState<SortCriterion>("margin_pct");
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const base = budgetMax !== null
      ? cells.filter((c) => c.price_net <= budgetMax)
      : cells;
    return sortCells(base, sortBy);
  }, [cells, budgetMax, sortBy]);

  if (cells.length === 0) return null;

  return (
    <div className="mt-5 pt-4 border-t border-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h5 className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
          Ranking opcji
          <span className="text-slate-300 font-normal ml-1">
            ({filtered.length} wyników)
          </span>
        </h5>

        {/* Sort buttons */}
        <div className="flex gap-1">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setSortBy(opt.key)}
              className={`text-[9px] font-bold px-2.5 py-1 rounded-full transition-all ${
                sortBy === opt.key
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="space-y-2">
        {filtered.length === 0 && (
          <div className="text-center py-6 text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
            Brak opcji w tym budżecie. Zwiększ limit.
          </div>
        )}

        {filtered.map((cell, idx) => {
          const key = `${cell.months}_${cell.km_per_year}`;
          const marginPct = cell.marza_na_kontrakcie_pct * 100;
          const tier = getMarginTier(marginPct);
          const isExpanded = expandedKey === key;
          const medal = idx < 3 ? MEDALS[idx] : null;

          // Visual progress bar for margin
          const barWidth = Math.max(Math.min(marginPct / 25 * 100, 100), 2);

          return (
            <div key={key}>
              <button
                onClick={() => setExpandedKey(isExpanded ? null : key)}
                className={`w-full text-left rounded-xl transition-all duration-200 ${
                  isExpanded
                    ? `p-4 shadow-md border-2 ${tier.borderColor}`
                    : "p-3 border border-slate-200 hover:border-slate-300 hover:shadow-sm"
                }`}
                style={{
                  backgroundColor: isExpanded ? tier.heatBg : undefined,
                }}
              >
                <div className="flex items-center gap-3">
                  {/* Rank */}
                  <div className="w-8 text-center flex-shrink-0">
                    {medal ? (
                      <span className="text-lg">{medal}</span>
                    ) : (
                      <span className="text-[10px] font-bold text-slate-300">
                        #{idx + 1}
                      </span>
                    )}
                  </div>

                  {/* Config */}
                  <div className="min-w-[80px]">
                    <div className="text-xs font-bold text-slate-700">
                      {cell.months} mc
                    </div>
                    <div className="text-[9px] text-slate-400">
                      {fmtKm(cell.km_per_year)} km/rok • {fmtKm(cell.total_km)} km
                    </div>
                  </div>

                  {/* Margin bar */}
                  <div className="flex-1 min-w-[100px]">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${barWidth}%`,
                            backgroundColor: tier.heatColor,
                          }}
                        />
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${tier.badgeBg} ${tier.badgeText}`}
                      >
                        {marginPct.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Price */}
                  <div className="text-right min-w-[90px]">
                    <div className="text-sm font-black text-blue-700 tabular-nums">
                      {fmtPLN(cell.price_net)}
                      <span className="text-[8px] text-slate-400 font-normal ml-0.5">
                        PLN
                      </span>
                    </div>
                    <div className="text-[9px] text-slate-400">
                      marża:{" "}
                      <span
                        className={`font-bold ${
                          cell.marza_na_kontrakcie >= 0
                            ? "text-emerald-600"
                            : "text-red-600"
                        }`}
                      >
                        {fmtPLN2(cell.marza_na_kontrakcie)}
                      </span>
                    </div>
                  </div>

                  {/* Chevron */}
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                </div>
              </button>

              {isExpanded && <CostBreakdownPanel cell={cell} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
