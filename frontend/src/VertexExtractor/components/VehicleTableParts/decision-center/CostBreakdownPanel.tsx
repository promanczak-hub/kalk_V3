import type { MiniMatrixCell } from "./decision-center.types";
import { fmtPLN2, getMarginTier } from "./decision-center.utils";
import { AccordionBreakdown } from "./AccordionBreakdown";

interface CostBreakdownPanelProps {
  cell: MiniMatrixCell;
}

// ── SVG Donut Chart ──────────────────────────────────────────────────────────

function DonutChart({
  revenue,
  cost,
  margin,
  marginPct,
}: {
  revenue: number;
  cost: number;
  margin: number;
  marginPct: number;
}) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const total = revenue > 0 ? revenue : 1;
  const costRatio = Math.min(cost / total, 1);
  const costDash = costRatio * circumference;
  const marginDash = circumference - costDash;
  const tier = getMarginTier(marginPct);
  const isNegative = margin < 0;

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        {/* Cost arc */}
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="14"
          strokeDasharray={`${costDash} ${marginDash}`}
          strokeDashoffset={circumference / 4}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
        {/* Margin arc */}
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={isNegative ? "#ef4444" : tier.heatColor}
          strokeWidth="14"
          strokeDasharray={`${marginDash} ${costDash}`}
          strokeDashoffset={circumference / 4 - costDash}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
        {/* Center text */}
        <text x="70" y="62" textAnchor="middle" className="fill-slate-800 text-sm font-black">
          {marginPct.toFixed(1)}%
        </text>
        <text x="70" y="80" textAnchor="middle" className="fill-slate-400 text-[9px] font-semibold">
          MARŻA
        </text>
      </svg>
      <div className="text-center mt-1">
        <span className={`text-xs font-bold ${isNegative ? "text-red-600" : tier.textColor}`}>
          {fmtPLN2(margin)} PLN
        </span>
      </div>
    </div>
  );
}

// ── Stacked Bar Chart ────────────────────────────────────────────────────────

interface BarSegment {
  label: string;
  value: number;
  color: string;
}

function StackedBar({ segments }: { segments: BarSegment[] }) {
  const total = segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0);
  if (total <= 0) return null;

  return (
    <div>
      {/* Bar */}
      <div className="flex h-6 rounded-full overflow-hidden shadow-inner bg-slate-100">
        {segments.map((seg) => {
          const pct = total > 0 ? (Math.max(seg.value, 0) / total) * 100 : 0;
          if (pct < 0.5) return null;
          return (
            <div
              key={seg.label}
              className="h-full transition-all duration-500 first:rounded-l-full last:rounded-r-full relative group"
              style={{ width: `${pct}%`, backgroundColor: seg.color }}
            >
              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-white text-[9px] font-semibold rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                {seg.label}: {fmtPLN2(seg.value)} PLN
              </div>
            </div>
          );
        })}
      </div>

      {/* Labels */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2.5">
        {segments.map((seg) =>
          seg.value > 0 ? (
            <div key={seg.label} className="flex items-center gap-1.5">
              <div
                className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{ backgroundColor: seg.color }}
              />
              <span className="text-[9px] text-slate-500 font-medium">
                {seg.label}
              </span>
              <span className="text-[9px] text-slate-700 font-bold tabular-nums">
                {fmtPLN2(seg.value)}
              </span>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}

// ── Main Panel ───────────────────────────────────────────────────────────────

export function CostBreakdownPanel({ cell }: CostBreakdownPanelProps) {
  const marginPct = cell.marza_na_kontrakcie_pct * 100;
  const revenue = cell.price_net * cell.months;
  const bd = cell.breakdown;

  const segments: BarSegment[] = [
    { label: "Finanse", value: bd.finance.price, color: "#3b82f6" },
    { label: "Serwis", value: bd.technical.service.price, color: "#8b5cf6" },
    { label: "Opony", value: bd.technical.tires.price, color: "#06b6d4" },
    { label: "Ubezpieczenie", value: bd.technical.insurance.price, color: "#f59e0b" },
    { label: "Auto zastępcze", value: bd.technical.replacement_car.price, color: "#ec4899" },
    { label: "Koszty dodatkowe", value: bd.technical.additional_costs.price, color: "#64748b" },
  ];

  return (
    <div className="mt-3 p-5 bg-white rounded-xl border border-slate-200 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
      <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-4">
        Rozkład kosztów — {cell.months} mc • {cell.km_per_year / 1000}k km/rok
      </h5>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_180px] gap-6 items-start">
        {/* Left: stacked bar */}
        <div>
          <p className="text-[10px] text-slate-500 font-semibold uppercase mb-2">
            Struktura stawki miesięcznej
          </p>
          <StackedBar segments={segments} />

          {/* Extra KPIs under bar */}
          <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-100">
            <div>
              <p className="text-[9px] text-slate-400 uppercase font-semibold">Czynsz fin.</p>
              <p className="text-xs font-bold text-slate-700 tabular-nums">{fmtPLN2(cell.czynsz_finansowy)}</p>
            </div>
            <div>
              <p className="text-[9px] text-slate-400 uppercase font-semibold">Czynsz tech.</p>
              <p className="text-xs font-bold text-slate-700 tabular-nums">{fmtPLN2(cell.czynsz_techniczny)}</p>
            </div>
            <div>
              <p className="text-[9px] text-slate-400 uppercase font-semibold">WR SAMAR</p>
              <p className="text-xs font-bold text-slate-700 tabular-nums">{fmtPLN2(cell.rv_samar_net)}</p>
            </div>
          </div>
        </div>

        {/* Right: donut */}
        <div>
          <p className="text-[10px] text-slate-500 font-semibold uppercase mb-2 text-center">
            Przychód vs koszty
          </p>
          <DonutChart
            revenue={revenue}
            cost={cell.koszty_ogolem}
            margin={cell.marza_na_kontrakcie}
            marginPct={marginPct}
          />
        </div>
      </div>

      {/* Accordion drill-down */}
      <AccordionBreakdown cell={cell} />
    </div>
  );
}
