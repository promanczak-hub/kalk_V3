import type { MiniMatrixCell } from "./decision-center.types";

interface DecisionCenterKPIProps {
  cells: MiniMatrixCell[];
  selectedCell: MiniMatrixCell | null;
  tireClass: string;
  budgetMax: number | null;
}

function fmtNum(v: number): string {
  return v.toLocaleString("pl-PL", { maximumFractionDigits: 0 });
}

function Badge({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200">
      <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
        {label}
      </span>
      <span className="text-xs font-bold text-slate-700 tabular-nums">
        {value}
      </span>
    </div>
  );
}

export function DecisionCenterKPI({
  cells,
  selectedCell,
  tireClass,
}: DecisionCenterKPIProps) {
  if (cells.length === 0) return null;

  // Cheapest option
  const cheapest = cells.reduce((a, b) =>
    a.price_net < b.price_net ? a : b
  );

  // If a cell is selected, show its data; otherwise show cheapest
  const activeCell = selectedCell || cheapest;

  // Tire info: show per-cell count + cost from backend
  const tireData = activeCell.breakdown.technical.tires;
  const tireSets = tireData.ilosc_opon ?? 0;
  const tireLabel = tireSets > 0
    ? `${tireSets} kpl • ${fmtNum(Math.round(tireData.price))} PLN/mc`
    : `${tireClass}`;

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <Badge
        label="Stawka"
        value={`${fmtNum(activeCell.price_net)} PLN`}
      />
      <Badge
        label="Przebieg"
        value={`${fmtNum(activeCell.total_km)} km`}
      />
      <Badge
        label="Opony"
        value={tireLabel}
      />
      <Badge
        label="Marża"
        value={`${(activeCell.marza_na_kontrakcie_pct * 100).toFixed(1)}%`}
      />
    </div>
  );
}
