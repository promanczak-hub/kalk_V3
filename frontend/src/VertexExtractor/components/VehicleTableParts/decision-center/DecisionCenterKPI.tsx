import { TrendingDown, TrendingUp, Star, Target } from "lucide-react";
import type { MiniMatrixCell } from "./decision-center.types";
import { fmtPLN, fmtKm, findBestCell, getMarginTier } from "./decision-center.utils";
import { Sparkline } from "./Sparkline";

interface DecisionCenterKPIProps {
  cells: MiniMatrixCell[];
  budgetMax: number | null;
}

interface KPICardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  subtitle: string;
  gradient: string;
  sparkData?: number[];
  sparkColor?: string;
}

function KPICard({ icon, label, value, subtitle, gradient, sparkData, sparkColor }: KPICardProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl p-4 ${gradient} border border-white/20 shadow-sm`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-white/70 mb-1">
            {label}
          </p>
          <div className="flex items-center">
            <p className="text-xl font-black text-white tabular-nums leading-tight">
              {value}
            </p>
            {sparkData && sparkData.length >= 2 && (
              <Sparkline
                data={sparkData}
                width={56}
                height={22}
                strokeColor={sparkColor || "rgba(255,255,255,0.8)"}
                fillColor={sparkColor ? `${sparkColor}20` : "rgba(255,255,255,0.1)"}
              />
            )}
          </div>
          <p className="text-[10px] text-white/60 mt-1">{subtitle}</p>
        </div>
        <div className="p-2 rounded-lg bg-white/10 backdrop-blur-sm flex-shrink-0">
          {icon}
        </div>
      </div>
    </div>
  );
}

export function DecisionCenterKPI({ cells, budgetMax }: DecisionCenterKPIProps) {
  if (cells.length === 0) return null;

  // Lowest price
  const cheapest = cells.reduce((a, b) =>
    a.price_net < b.price_net ? a : b
  );

  // Highest margin
  const highestMargin = cells.reduce((a, b) =>
    a.marza_na_kontrakcie_pct > b.marza_na_kontrakcie_pct ? a : b
  );
  const highMarginPct = highestMargin.marza_na_kontrakcie_pct * 100;
  const tier = getMarginTier(highMarginPct);

  // AI pick
  const bestCell = findBestCell(cells);

  // Budget count
  const inBudget = budgetMax
    ? cells.filter((c) => c.price_net <= budgetMax).length
    : cells.length;

  // Sparkline trends: group by months, take cheapest price per month
  const monthGroups = new Map<number, MiniMatrixCell[]>();
  for (const c of cells) {
    const arr = monthGroups.get(c.months) || [];
    arr.push(c);
    monthGroups.set(c.months, arr);
  }
  const sortedMonths = [...monthGroups.keys()].sort((a, b) => a - b);
  const priceTrend = sortedMonths.map((m) => {
    const group = monthGroups.get(m)!;
    return Math.min(...group.map((c) => c.price_net));
  });
  const marginTrend = sortedMonths.map((m) => {
    const group = monthGroups.get(m)!;
    return Math.max(...group.map((c) => c.marza_na_kontrakcie_pct * 100));
  });

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <KPICard
        icon={<TrendingDown className="w-5 h-5 text-white/80" />}
        label="Najniższa stawka"
        value={`${fmtPLN(cheapest.price_net)} PLN`}
        subtitle={`${cheapest.months} mc • ${fmtKm(cheapest.km_per_year)} km/rok`}
        gradient="bg-gradient-to-br from-blue-600 to-blue-800"
        sparkData={priceTrend}
        sparkColor="rgba(147,197,253,0.9)"
      />
      <KPICard
        icon={<TrendingUp className="w-5 h-5 text-white/80" />}
        label="Najwyższa marża"
        value={`${highMarginPct.toFixed(1)}%`}
        subtitle={`${tier.label} • ${highestMargin.months} mc`}
        gradient="bg-gradient-to-br from-emerald-600 to-emerald-800"
        sparkData={marginTrend}
        sparkColor="rgba(110,231,183,0.9)"
      />
      <KPICard
        icon={<Star className="w-5 h-5 text-white/80" />}
        label="Rekomendacja AI"
        value={bestCell ? `${bestCell.months}mc / ${fmtKm(bestCell.km_per_year)}` : "—"}
        subtitle={
          bestCell
            ? `${fmtPLN(bestCell.price_net)} PLN • ${(bestCell.marza_na_kontrakcie_pct * 100).toFixed(1)}%`
            : "Brak danych"
        }
        gradient="bg-gradient-to-br from-violet-600 to-purple-800"
      />
      <KPICard
        icon={<Target className="w-5 h-5 text-white/80" />}
        label="Opcji w budżecie"
        value={`${inBudget} / ${cells.length}`}
        subtitle={budgetMax ? `budżet ≤ ${fmtPLN(budgetMax)} PLN` : "bez filtra budżetowego"}
        gradient="bg-gradient-to-br from-amber-500 to-orange-700"
      />
    </div>
  );
}
