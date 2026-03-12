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
    a.LacznaStawka < b.LacznaStawka ? a : b
  );

  // If a cell is selected, show its data; otherwise show cheapest
  const activeCell = selectedCell || cheapest;

  // Tire info: single string
  const tireSets = activeCell.IloscOpon ?? 0;
  const tireCost = activeCell.Opony ?? 0;
  const tireLabel = tireSets > 0
    ? `${tireSets} kpl • ${fmtNum(Math.round(tireCost))} PLN/mc`
    : `${tireClass}`;

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <Badge
        label="Stawka"
        value={`${fmtNum(activeCell.LacznaStawka)} PLN`}
      />
      <Badge
        label="Przebieg"
        value={`${fmtNum((activeCell.Przebieg / 12) * activeCell.Okres)} km`}
      />
      <Badge
        label="Opony"
        value={tireLabel}
      />
      <Badge
        label="Amortyzacja"
        value={`${(activeCell.AmortyzacjaProcent * 100).toFixed(2)}%`}
      />
      <Badge
        label="Marża"
        value={`${(activeCell.MarzaNaKontrakcieProcent * 100).toFixed(1)}%`}
      />
    </div>
  );
}
