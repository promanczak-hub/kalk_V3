import { useState } from "react";
import { Wallet } from "lucide-react";
import { fmtPLN } from "./decision-center.utils";

interface BudgetFilterProps {
  priceMin: number;
  priceMax: number;
  budgetMax: number | null;
  onBudgetChange: (budget: number | null) => void;
}

export function BudgetFilter({
  priceMin,
  priceMax,
  budgetMax,
  onBudgetChange,
}: BudgetFilterProps) {
  const [isActive, setIsActive] = useState(budgetMax !== null);
  const step = 50;

  const handleToggle = () => {
    if (isActive) {
      onBudgetChange(null);
      setIsActive(false);
    } else {
      onBudgetChange(priceMax);
      setIsActive(true);
    }
  };

  // Percentage for gradient fill
  const range = priceMax - priceMin || 1;
  const fillPct = budgetMax !== null
    ? ((budgetMax - priceMin) / range) * 100
    : 100;

  return (
    <div className="mb-4 p-4 rounded-xl bg-gradient-to-r from-slate-50 to-blue-50/50 border border-slate-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Wallet className="w-4 h-4 text-blue-600" />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
            Budżet klienta
          </span>
        </div>
        <button
          onClick={handleToggle}
          className={`text-[10px] font-bold px-3 py-1 rounded-full transition-all ${
            isActive
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-500 hover:bg-slate-200"
          }`}
        >
          {isActive ? "Aktywny ✓" : "Włącz"}
        </button>
      </div>

      {isActive && (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-slate-400 font-semibold tabular-nums w-16">
              {fmtPLN(priceMin)}
            </span>

            {/* Custom styled range */}
            <div className="flex-1 relative h-3">
              {/* Track background */}
              <div className="absolute inset-0 rounded-full bg-slate-200" />
              {/* Filled track */}
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-150"
                style={{ width: `${fillPct}%` }}
              />
              {/* Native range (invisible, over the top for interaction) */}
              <input
                type="range"
                min={priceMin}
                max={priceMax}
                step={step}
                value={budgetMax || priceMax}
                onChange={(e) => onBudgetChange(parseInt(e.target.value))}
                className="absolute inset-0 w-full opacity-0 cursor-pointer"
              />
              {/* Thumb visual */}
              <div
                className="absolute top-1/2 -translate-y-1/2 w-5 h-5 bg-white border-2 border-blue-600 rounded-full shadow-md pointer-events-none transition-all duration-150"
                style={{ left: `calc(${fillPct}% - 10px)` }}
              />
            </div>

            <span className="text-[10px] text-slate-400 font-semibold tabular-nums w-16 text-right">
              {fmtPLN(priceMax)}
            </span>
          </div>

          {/* Current value */}
          <div className="text-center">
            <span className="text-sm font-black text-blue-700 tabular-nums">
              ≤ {fmtPLN(budgetMax || priceMax)} PLN
            </span>
            <span className="text-[10px] text-slate-400 ml-1.5">/ miesiąc netto</span>
          </div>
        </div>
      )}
    </div>
  );
}
