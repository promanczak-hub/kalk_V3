import { Star } from "lucide-react";
import type { MiniMatrixCell } from "./decision-center.types";
import { fmtPLN, fmtKm, getMarginTier, findBestCell } from "./decision-center.utils";

interface HeatmapMatrixProps {
  cells: MiniMatrixCell[];
  targetMonths: number[];
  targetKmPerYear: number[];
  selectedKey: string | null;
  onCellSelect: (key: string | null) => void;
  budgetMax: number | null;
}

export function HeatmapMatrix({
  cells,
  targetMonths,
  targetKmPerYear,
  selectedKey,
  onCellSelect,
  budgetMax,
}: HeatmapMatrixProps) {
  const cellMap = new Map<string, MiniMatrixCell>();
  for (const c of cells) {
    cellMap.set(`${c.months}_${c.km_per_year}`, c);
  }

  const bestCell = findBestCell(cells);
  const bestKey = bestCell
    ? `${bestCell.months}_${bestCell.km_per_year}`
    : null;

  // Legend tiers
  const legendTiers = [
    { pct: -1, label: "< 0%" },
    { pct: 4, label: "0–8%" },
    { pct: 10, label: "8–12%" },
    { pct: 13, label: "12–15%" },
    { pct: 17, label: "15–20%" },
    { pct: 25, label: "> 20%" },
  ];

  return (
    <div className="mb-5">
      {/* Matrix grid */}
      <div className="overflow-x-auto">
        <table className="w-full border-separate" style={{ borderSpacing: "6px" }}>
          <thead>
            <tr>
              <th className="py-2 px-3 text-left text-[10px] font-bold uppercase text-slate-400 tracking-wider w-20">
                Okres
              </th>
              {targetKmPerYear.map((km) => (
                <th
                  key={km}
                  className="py-2 text-center text-[10px] font-bold uppercase text-slate-400 tracking-wider"
                >
                  {km / 1000}k km/rok
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {targetMonths.map((months) => (
              <tr key={months}>
                <td className="py-2 px-3 text-xs font-bold text-slate-600">
                  {months} mc
                </td>
                {targetKmPerYear.map((km) => {
                  const key = `${months}_${km}`;
                  const cell = cellMap.get(key);
                  if (!cell) {
                    return (
                      <td key={km} className="text-center">
                        <div className="rounded-xl p-3 bg-slate-50 border border-dashed border-slate-200">
                          <span className="text-xs text-slate-300">—</span>
                        </div>
                      </td>
                    );
                  }

                  const marginPct = cell.marza_na_kontrakcie_pct * 100;
                  const tier = getMarginTier(marginPct);
                  const isSelected = selectedKey === key;
                  const isBest = bestKey === key;
                  const isOutOfBudget =
                    budgetMax !== null && cell.price_net > budgetMax;

                  return (
                    <td key={km} className="text-center">
                      <button
                        onClick={() =>
                          onCellSelect(isSelected ? null : key)
                        }
                        className={`
                          relative w-full rounded-xl p-3 transition-all duration-200
                          cursor-pointer group
                          ${isOutOfBudget ? "opacity-35 grayscale" : ""}
                          ${
                            isSelected
                              ? "ring-2 ring-blue-500 ring-offset-2 shadow-lg scale-[1.03]"
                              : "hover:shadow-md hover:scale-[1.02]"
                          }
                        `}
                        style={{
                          backgroundColor: tier.heatBg,
                          borderWidth: "2px",
                          borderStyle: "solid",
                          borderColor: isSelected
                            ? tier.heatColor
                            : `${tier.heatColor}40`,
                        }}
                      >
                        {/* AI crown */}
                        {isBest && (
                          <div className="absolute -top-2 -right-2 z-10">
                            <div className="bg-amber-400 rounded-full p-1 shadow-md">
                              <Star className="w-3 h-3 text-white fill-white" />
                            </div>
                          </div>
                        )}

                        {/* Price */}
                        <div className="text-lg font-black tabular-nums" style={{ color: tier.heatColor }}>
                          {fmtPLN(cell.price_net)}
                        </div>

                        {/* Small info */}
                        <div className="text-[9px] text-slate-400 mt-0.5">
                          {fmtKm(cell.total_km)} km
                        </div>

                        {/* Margin badge */}
                        <div className="mt-1.5">
                          <span
                            className={`inline-block text-[9px] font-bold px-2 py-0.5 rounded-full ${tier.badgeBg} ${tier.badgeText}`}
                          >
                            {marginPct.toFixed(1)}%
                          </span>
                        </div>

                        {/* Hover tooltip: margin PLN */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 text-white text-[10px] rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-20">
                          Marża: {fmtPLN(cell.marza_na_kontrakcie)} PLN
                          <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45 -mt-1" />
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
        {legendTiers.map((t) => {
          const tier = getMarginTier(t.pct);
          return (
            <span
              key={t.label}
              className={`text-[9px] font-semibold px-2 py-0.5 rounded-full ${tier.badgeBg} ${tier.badgeText}`}
            >
              {t.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
