import { Car, Route, Calendar, Banknote } from "lucide-react";

interface StickyContextHeaderProps {
  brand: string;
  model: string;
  basePriceNet: number;
  baseMonths: number;
  baseKmTotal: number;
}

function fmtPrice(v: number): string {
  return v.toLocaleString("pl-PL", { maximumFractionDigits: 0 });
}

export function StickyContextHeader({
  brand,
  model,
  basePriceNet,
  baseMonths,
  baseKmTotal,
}: StickyContextHeaderProps) {
  const kmPerYear = baseMonths > 0 ? Math.round((baseKmTotal / baseMonths) * 12) : 0;

  return (
    <div className="sticky top-0 z-10 -mx-5 -mt-5 mb-4 px-5 py-2 bg-white/95 backdrop-blur-sm border-b border-slate-200 flex items-center gap-4 flex-wrap">
      {/* Vehicle name */}
      <div className="flex items-center gap-1.5 min-w-0">
        <Car className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        <span className="text-[11px] font-bold text-slate-700 truncate">
          {brand} {model}
        </span>
      </div>

      <div className="h-3 w-px bg-slate-200 hidden sm:block" />

      {/* Mileage */}
      <div className="flex items-center gap-1">
        <Route className="w-3 h-3 text-slate-400 flex-shrink-0" />
        <span className="text-[10px] text-slate-400">Przebieg</span>
        <span className="text-[10px] font-semibold text-slate-600 tabular-nums">
          {fmtPrice(kmPerYear)} km/rok
        </span>
      </div>

      <div className="h-3 w-px bg-slate-200 hidden sm:block" />

      {/* Period */}
      <div className="flex items-center gap-1">
        <Calendar className="w-3 h-3 text-slate-400 flex-shrink-0" />
        <span className="text-[10px] text-slate-400">Okres</span>
        <span className="text-[10px] font-semibold text-slate-600 tabular-nums">{baseMonths} mc</span>
      </div>

      <div className="h-3 w-px bg-slate-200 hidden sm:block" />

      {/* Price */}
      <div className="flex items-center gap-1">
        <Banknote className="w-3 h-3 text-slate-400 flex-shrink-0" />
        <span className="text-[10px] text-slate-400">Cena kat.</span>
        <span className="text-[10px] font-semibold text-slate-600 tabular-nums">
          {fmtPrice(basePriceNet)} netto
        </span>
      </div>
    </div>
  );
}
