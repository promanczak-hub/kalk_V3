import { useState, useCallback, useRef } from "react";
import { SlidersHorizontal, RotateCcw, Gauge, Route, Percent } from "lucide-react";

/* ── Types ───────────────────────────────────────────────────────────── */

export interface MatrixFilters {
  monthsRange: [number, number];
  targetKmPerYear: number | null;
  globalMarginPct: number;
}

interface MatrixFilterToolbarProps {
  defaultMarginPct: number;
  filters: MatrixFilters;
  onFiltersChange: (f: MatrixFilters) => void;
  onMarginRecalculate: (marginPct: number) => void;
  onExactRecalculate: (months: number, kmPerYear: number, marginPct: number) => void;
  isRecalculating: boolean;
}

/* ── Constants ──────────────────────────────────────────────────────── */

const MONTHS_MIN = 12;
const MONTHS_MAX = 84;
const MONTHS_STEP = 12;
const MONTHS_TICKS = [12, 24, 36, 48, 60, 72, 84];

const KM_MIN = 40_000;
const KM_MAX = 80_000;
const KM_STEP = 5_000;
const KM_MARGIN_PCT = 0.05;

const MARGIN_MIN = 0;
const MARGIN_MAX = 30;
const MARGIN_STEP = 0.5;

/* ── Helpers ─────────────────────────────────────────────────────────── */

function fmtKm(v: number): string {
  return `${(v / 1000).toFixed(0)}k`;
}

function getMarginSliderColor(pct: number): string {
  if (pct < 8) return "#ef4444";
  if (pct < 12) return "#f97316";
  return "#22c55e";
}

function pctOfRange(val: number, min: number, max: number): number {
  return ((val - min) / (max - min)) * 100;
}

/* ── Dual-Range Slider (reusable) ─────────────────────────────────── */

function DualRangeSlider({
  min,
  max,
  step,
  value,
  onChange,
  ticks,
  formatTick,
}: {
  min: number;
  max: number;
  step: number;
  value: [number, number];
  onChange: (v: [number, number]) => void;
  ticks?: number[];
  formatTick?: (v: number) => string;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<"low" | "high" | null>(null);

  const snapToStep = useCallback((raw: number) => Math.round(raw / step) * step, [step]);

  const getValueFromX = useCallback(
    (clientX: number) => {
      if (!trackRef.current) return min;
      const rect = trackRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      return snapToStep(min + pct * (max - min));
    },
    [min, max, snapToStep],
  );

  const handlePointerDown = (thumb: "low" | "high") => (e: React.PointerEvent) => {
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    setDragging(thumb);
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging) return;
      const v = getValueFromX(e.clientX);
      if (dragging === "low") {
        onChange([Math.min(v, value[1]), value[1]]);
      } else {
        onChange([value[0], Math.max(v, value[0])]);
      }
    },
    [dragging, getValueFromX, onChange, value],
  );

  const handlePointerUp = () => setDragging(null);

  const lowPct = pctOfRange(value[0], min, max);
  const highPct = pctOfRange(value[1], min, max);

  return (
    <div className="relative pt-2 pb-4">
      {/* Track */}
      <div
        ref={trackRef}
        className="relative h-2 rounded-full bg-slate-200 cursor-pointer"
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        {/* Filled range */}
        <div
          className="absolute inset-y-0 rounded-full bg-gradient-to-r from-blue-400 to-blue-600"
          style={{ left: `${lowPct}%`, right: `${100 - highPct}%` }}
        />

        {/* Low thumb */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-white border-2 border-blue-600 shadow-md cursor-grab transition-shadow ${dragging === "low" ? "shadow-lg ring-2 ring-blue-300 scale-110" : "hover:shadow-lg"}`}
          style={{ left: `calc(${lowPct}% - 10px)` }}
          onPointerDown={handlePointerDown("low")}
        />

        {/* High thumb */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-white border-2 border-blue-600 shadow-md cursor-grab transition-shadow ${dragging === "high" ? "shadow-lg ring-2 ring-blue-300 scale-110" : "hover:shadow-lg"}`}
          style={{ left: `calc(${highPct}% - 10px)` }}
          onPointerDown={handlePointerDown("high")}
        />
      </div>

      {/* Ticks */}
      {ticks && (
        <div className="flex justify-between mt-1.5 px-0">
          {ticks.map((t) => {
            const inRange = t >= value[0] && t <= value[1];
            return (
              <span
                key={t}
                className={`text-[9px] font-semibold tabular-nums transition-colors ${inRange ? "text-blue-600" : "text-slate-300"}`}
              >
                {formatTick ? formatTick(t) : t}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Single Slider ──────────────────────────────────────────────────── */

function SingleSlider({
  min,
  max,
  step,
  value,
  onChange,
  formatValue,
  fillColor = "from-emerald-400 to-emerald-600",
  thumbColor = "border-emerald-600",
}: {
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  formatValue?: (v: number) => string;
  fillColor?: string;
  thumbColor?: string;
}) {
  const pct = pctOfRange(value, min, max);

  return (
    <div className="relative pt-2 pb-1">
      <div className="relative h-2 rounded-full bg-slate-200">
        {/* Fill */}
        <div
          className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${fillColor} transition-all duration-100`}
          style={{ width: `${pct}%` }}
        />
        {/* Native range */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
        />
        {/* Thumb visual */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-white border-2 ${thumbColor} shadow-md pointer-events-none transition-all duration-100`}
          style={{ left: `calc(${pct}% - 10px)` }}
        />
      </div>
      {formatValue && (
        <div className="text-center mt-1.5">
          <span className="text-xs font-bold text-slate-700 tabular-nums">
            {formatValue(value)}
          </span>
        </div>
      )}
    </div>
  );
}

/* ── Main Toolbar Component ─────────────────────────────────────────── */

export function MatrixFilterToolbar({
  defaultMarginPct,
  filters,
  onFiltersChange,
  onMarginRecalculate,
  onExactRecalculate,
  isRecalculating,
}: MatrixFilterToolbarProps) {
  const [kmActive, setKmActive] = useState(filters.targetKmPerYear !== null);
  const [marginDirty, setMarginDirty] = useState(false);

  // Precision Variant state
  const [exactMonths, setExactMonths] = useState<string>("48");
  const [exactKm, setExactKm] = useState<string>("40000");
  const [exactMargin, setExactMargin] = useState<string>(defaultMarginPct.toFixed(2));

  const update = (partial: Partial<MatrixFilters>) => {
    onFiltersChange({ ...filters, ...partial });
  };

  const handleMarginChange = (v: number) => {
    update({ globalMarginPct: v });
    setMarginDirty(true);
  };

  const handleRecalculate = () => {
    onMarginRecalculate(filters.globalMarginPct);
    setMarginDirty(false);
  };

  const handleReset = () => {
    onFiltersChange({
      monthsRange: [MONTHS_MIN, MONTHS_MAX],
      targetKmPerYear: null,
      globalMarginPct: defaultMarginPct,
    });
    setKmActive(false);
    setMarginDirty(false);
  };

  const handleKmToggle = () => {
    if (kmActive) {
      update({ targetKmPerYear: null });
      setKmActive(false);
    } else {
      update({ targetKmPerYear: 60_000 });
      setKmActive(true);
    }
  };

  const handleExactRecalculateClick = () => {
    const m = parseInt(exactMonths, 10);
    const k = parseInt(exactKm, 10);
    const mar = parseFloat(exactMargin);
    if (!isNaN(m) && !isNaN(k) && !isNaN(mar)) {
      onExactRecalculate(m, k, mar);
    }
  };

  // Km range display
  const kmLow = filters.targetKmPerYear
    ? Math.round(filters.targetKmPerYear * (1 - KM_MARGIN_PCT))
    : null;
  const kmHigh = filters.targetKmPerYear
    ? Math.round(filters.targetKmPerYear * (1 + KM_MARGIN_PCT))
    : null;

  const isFiltered =
    filters.monthsRange[0] !== MONTHS_MIN ||
    filters.monthsRange[1] !== MONTHS_MAX ||
    filters.targetKmPerYear !== null ||
    filters.globalMarginPct !== defaultMarginPct;

  return (
    <div className="mb-4 rounded-2xl border border-slate-200/80 bg-gradient-to-br from-white via-slate-50/50 to-blue-50/30 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-100">
            <SlidersHorizontal className="w-4 h-4 text-blue-600" />
          </div>
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Filtry matrycy
          </span>
          {isFiltered && (
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-blue-600 text-white animate-in fade-in">
              Aktywne
            </span>
          )}
        </div>
        {isFiltered && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded-lg text-slate-500 bg-slate-100 hover:bg-slate-200 transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Resetuj
          </button>
        )}
      </div>

      {/* Controls grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-0 divide-y md:divide-y-0 md:divide-x divide-slate-100">
        {/* 1. Period dual-range slider */}
        <div className="px-5 py-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Gauge className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              Okres
            </span>
            <span className="ml-auto text-[10px] font-bold text-blue-700 tabular-nums">
              {filters.monthsRange[0]}–{filters.monthsRange[1]} mc
            </span>
          </div>
          <DualRangeSlider
            min={MONTHS_MIN}
            max={MONTHS_MAX}
            step={MONTHS_STEP}
            value={filters.monthsRange}
            onChange={(v) => update({ monthsRange: v })}
            ticks={MONTHS_TICKS}
            formatTick={(v) => `${v}`}
          />
        </div>

        {/* 2. Km/year slider with ±5% margin */}
        <div className="px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <Route className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Przebieg roczny
              </span>
            </div>
            <button
              onClick={handleKmToggle}
              className={`text-[9px] font-bold px-2.5 py-0.5 rounded-full transition-all ${
                kmActive
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-400 hover:bg-slate-200"
              }`}
            >
              {kmActive ? "Aktywny ✓" : "Włącz"}
            </button>
          </div>

          {kmActive && filters.targetKmPerYear !== null ? (
            <>
              <SingleSlider
                min={KM_MIN}
                max={KM_MAX}
                step={KM_STEP}
                value={filters.targetKmPerYear}
                onChange={(v) => update({ targetKmPerYear: v })}
                formatValue={(v) => `${fmtKm(v)} km/rok`}
                fillColor="from-emerald-400 to-emerald-600"
                thumbColor="border-emerald-600"
              />
              <div className="text-center mt-1">
                <span className="text-[9px] text-slate-400 font-medium">
                  Margines ±5%:{" "}
                  <span className="font-bold text-emerald-600">
                    {fmtKm(kmLow!)} – {fmtKm(kmHigh!)} km/rok
                  </span>
                </span>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-16 text-[10px] text-slate-300 font-medium">
              Filtr wyłączony — pokazuj wszystkie przebiegi
            </div>
          )}
        </div>

        {/* 3. Global margin slider — colored zones */}
        <div className="px-5 py-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Percent className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              Marża globalna
            </span>
            <span
              className="ml-auto text-[10px] font-bold tabular-nums"
              style={{ color: getMarginSliderColor(filters.globalMarginPct) }}
            >
              {filters.globalMarginPct.toFixed(1)}%
            </span>
          </div>
          {/* Colored zone margin slider */}
          <div className="relative pt-2 pb-1">
            <div className="relative h-2.5 rounded-full overflow-hidden">
              {/* Zone: Red 0-8% */}
              <div
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-red-400 to-red-500"
                style={{ width: `${pctOfRange(8, MARGIN_MIN, MARGIN_MAX)}%` }}
              />
              {/* Zone: Orange 8-12% */}
              <div
                className="absolute inset-y-0 bg-gradient-to-r from-orange-400 to-orange-500"
                style={{
                  left: `${pctOfRange(8, MARGIN_MIN, MARGIN_MAX)}%`,
                  width: `${pctOfRange(12, MARGIN_MIN, MARGIN_MAX) - pctOfRange(8, MARGIN_MIN, MARGIN_MAX)}%`,
                }}
              />
              {/* Zone: Green 12-30% */}
              <div
                className="absolute inset-y-0 right-0 bg-gradient-to-r from-emerald-400 to-emerald-500"
                style={{ left: `${pctOfRange(12, MARGIN_MIN, MARGIN_MAX)}%` }}
              />
              {/* Unselected overlay (dim area beyond current value) */}
              <div
                className="absolute inset-y-0 right-0 bg-slate-200/60"
                style={{ left: `${pctOfRange(filters.globalMarginPct, MARGIN_MIN, MARGIN_MAX)}%` }}
              />
            </div>
            {/* Native range input */}
            <input
              type="range"
              min={MARGIN_MIN}
              max={MARGIN_MAX}
              step={MARGIN_STEP}
              value={filters.globalMarginPct}
              onChange={(e) => handleMarginChange(parseFloat(e.target.value))}
              className="absolute inset-0 w-full opacity-0 cursor-pointer"
              style={{ top: "8px", height: "10px" }}
            />
            {/* Thumb */}
            <div
              className="absolute w-5 h-5 rounded-full bg-white shadow-lg pointer-events-none transition-all duration-100"
              style={{
                left: `calc(${pctOfRange(filters.globalMarginPct, MARGIN_MIN, MARGIN_MAX)}% - 10px)`,
                top: "4px",
                borderWidth: "3px",
                borderStyle: "solid",
                borderColor: getMarginSliderColor(filters.globalMarginPct),
              }}
            />
          </div>
          {/* Zone labels */}
          <div className="flex items-center justify-between mt-1 px-px">
            <span className="text-[8px] font-bold text-red-500 uppercase">0–8%</span>
            <span className="text-[8px] font-bold text-orange-500 uppercase">8–12%</span>
            <span className="text-[8px] font-bold text-emerald-500 uppercase">12–30%</span>
          </div>
          {marginDirty && (
            <button
              onClick={handleRecalculate}
              disabled={isRecalculating}
              className="mt-2 w-full flex items-center justify-center gap-1.5 text-[10px] font-bold px-3 py-1.5 rounded-lg text-white hover:brightness-110 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: getMarginSliderColor(filters.globalMarginPct) }}
            >
              {isRecalculating ? (
                <>
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Przeliczam…
                </>
              ) : (
                "⚡ Przelicz z nową marżą"
              )}
            </button>
          )}
        </div>
      </div>

      {/* Precision Variant Form */}
      <div className="border-t border-slate-100 bg-slate-50/50 px-5 py-3">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              Wariant precyzyjny:
            </span>
          </div>
          <div className="flex flex-1 items-center gap-3">
            <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-md px-2 py-1 shadow-sm">
              <label className="text-[10px] text-slate-400 font-semibold" htmlFor="exactMonths">Okres (mc):</label>
              <input
                id="exactMonths"
                type="number"
                min="6"
                max="120"
                value={exactMonths}
                onChange={(e) => setExactMonths(e.target.value)}
                className="w-12 text-xs font-bold text-slate-700 bg-transparent outline-none tabular-nums"
              />
            </div>
            <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-md px-2 py-1 shadow-sm">
              <label className="text-[10px] text-slate-400 font-semibold" htmlFor="exactKm">Przebieg (km/rok):</label>
              <input
                id="exactKm"
                type="number"
                min="10000"
                max="200000"
                step="1000"
                value={exactKm}
                onChange={(e) => setExactKm(e.target.value)}
                className="w-16 text-xs font-bold text-slate-700 bg-transparent outline-none tabular-nums"
              />
            </div>
            <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-md px-2 py-1 shadow-sm">
              <label className="text-[10px] text-slate-400 font-semibold" htmlFor="exactMargin">Marża (%):</label>
              <input
                id="exactMargin"
                type="number"
                min="-10"
                max="50"
                step="0.01"
                value={exactMargin}
                onChange={(e) => setExactMargin(e.target.value)}
                className="w-14 text-xs font-bold text-slate-700 bg-transparent outline-none tabular-nums"
              />
            </div>
            <button
              onClick={handleExactRecalculateClick}
              disabled={isRecalculating}
              className="ml-auto flex items-center gap-1 text-[10px] font-bold px-3 py-1.5 rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRecalculating ? "Przeliczam..." : "⚡ Wygeneruj wariant"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
