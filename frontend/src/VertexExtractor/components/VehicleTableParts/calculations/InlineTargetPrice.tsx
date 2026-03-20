import React, { useState } from "react";
import { TrendingUp } from "lucide-react";
import type { MiniMatrixCell } from "../decision-center/decision-center.types";

const MARGIN_LEVELS = [5, 8, 10, 12, 15, 18, 20, 25];

function marginColor(pct: number): string {
  if (pct < 0) return "#ef4444";
  if (pct < 8) return "#f97316";
  if (pct < 12) return "#eab308";
  if (pct < 15) return "#84cc16";
  if (pct < 20) return "#22c55e";
  return "#06b6d4";
}

function marginLabel(pct: number): string {
  if (pct < 0) return "Ujemna";
  if (pct < 8) return "Poniżej min.";
  if (pct < 12) return "Minimalna";
  if (pct < 15) return "Dobra";
  if (pct < 20) return "Bardzo dobra";
  return "Wysoka";
}

interface InlineTargetPriceProps {
  cell: MiniMatrixCell;
}

export function InlineTargetPrice({ cell }: InlineTargetPriceProps) {
  const [open, setOpen] = useState(false);
  const [targetInput, setTargetInput] = useState("");
  const baseCost = cell.KosztyLaczneMC;

  const targetPrice = parseFloat(targetInput.replace(",", ".")) || 0;
  const impliedMargin = targetPrice > 0 ? (1 - baseCost / targetPrice) * 100 : null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-200">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider hover:text-purple-600 transition-colors"
      >
        <span>💰 Jaka marża przy stawce docelowej?</span>
        <span className="text-[9px]">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-2 animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="flex items-center gap-2 mb-3">
            <div className="relative">
              <input
                type="number"
                placeholder="np. 3000"
                value={targetInput}
                onChange={(e) => setTargetInput(e.target.value)}
                className="w-28 text-sm font-semibold p-1.5 pr-10 border border-purple-200 rounded-lg outline-none focus:ring-2 focus:ring-purple-300 bg-white tabular-nums"
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-slate-400">PLN/mc</span>
            </div>
            <span className="text-[10px] text-slate-400 flex flex-col items-start gap-1">
              <span>Koszt bazowy:</span>
              <strong className="text-slate-600">
                {baseCost.toLocaleString("pl-PL", { maximumFractionDigits: 0 })} PLN
              </strong>
            </span>
          </div>

          {impliedMargin !== null && (
            <div className="space-y-2">
              <div
                className="flex items-center gap-3 p-2.5 rounded-lg"
                style={{
                  background: `${marginColor(impliedMargin)}12`,
                  border: `1px solid ${marginColor(impliedMargin)}30`,
                }}
              >
                <TrendingUp className="w-4 h-4 shrink-0" style={{ color: marginColor(impliedMargin) }} />
                <div>
                  <span className="text-base font-black tabular-nums" style={{ color: marginColor(impliedMargin) }}>
                    {impliedMargin.toFixed(1)}%
                  </span>
                  <span className="ml-2 text-[10px] font-semibold text-slate-500">
                    {marginLabel(impliedMargin)}
                  </span>
                </div>
                <div className="ml-auto text-right flex flex-col items-end">
                  <span className="text-[10px] text-slate-400 pb-0.5">przy docelowej</span>
                  <div className="text-[9px] text-slate-600 font-bold tabular-nums">
                    {targetPrice.toLocaleString("pl-PL")} PLN
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-1 mt-3">
                {MARGIN_LEVELS.slice(0, 8).map((m) => {
                  const price = Math.round(baseCost / (1 - m / 100));
                  const isTarget =
                    impliedMargin >= m - 1.5 && impliedMargin < m + 2;
                  return (
                    <div
                      key={m}
                      className="p-1.5 rounded text-center transition-colors hover:bg-slate-50"
                      style={{
                        background: `${marginColor(m)}10`,
                        border: `1px solid ${isTarget ? marginColor(m) : marginColor(m) + "30"}`,
                        boxShadow: isTarget
                          ? `0 0 0 1.5px ${marginColor(m)}60`
                          : undefined,
                      }}
                    >
                      <div className="text-[9px] font-bold mb-0.5" style={{ color: marginColor(m) }}>
                        {m}%
                      </div>
                      <div className="text-[10px] font-extrabold text-slate-700 tabular-nums">
                        {price.toLocaleString("pl-PL")}
                      </div>
                      <div className="text-[7px] text-slate-400 mt-0.5">PLN</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
