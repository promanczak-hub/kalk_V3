import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Loader2, LayoutDashboard } from "lucide-react";
import type { FleetVehicleView } from "../../types";
import type { MiniMatrixCell } from "./decision-center/decision-center.types";
import { DecisionCenterKPI } from "./decision-center/DecisionCenterKPI";
import { HeatmapMatrix } from "./decision-center/HeatmapMatrix";
import { CostBreakdownPanel } from "./decision-center/CostBreakdownPanel";
import { BudgetFilter } from "./decision-center/BudgetFilter";
import { RankingList } from "./decision-center/RankingList";
import { StickyContextHeader } from "./decision-center/StickyContextHeader";
import { ExploreMatrixButton } from "./decision-center/ExploreMatrixButton";

// ── Props ────────────────────────────────────────────────────────────────────

interface RentalRatesMiniMatrixProps {
  vehicle: FleetVehicleView;
  basePriceNet: number;
  defaultMarginPct: number;
  wiborPct: number;
  marginPct: number;
  depreciationPct: number;
  initialDepositPct: number;
  replacementCar: boolean;
  gpsRequired: boolean;
  hookInstallation: boolean;
  includeServicing: boolean;
  tireClass: string;
  tireCountMode: string;
  tireCostCorrectionEnabled: boolean;
  tireCostCorrection: number;
  rimDiameter: number | null;
  serviceCostType: "ASO" | "nonASO";
  vehicleVintage: "current" | "previous";
  isMetalic: boolean;
  discountPct: number;
  factoryOptions: { name: string; price_net: number; no_discount?: boolean; include_in_wr?: boolean }[];
  serviceOptions: { name: string; price_net: number; include_in_wr?: boolean }[];
}

// ── Constants ────────────────────────────────────────────────────────────────

const TARGET_MONTHS = [36, 48, 60];
const TARGET_KM_PER_YEAR = [30000, 40000, 50000, 60000];
const DEBOUNCE_MS = 600;

// ── Component ────────────────────────────────────────────────────────────────

export function RentalRatesMiniMatrix(props: RentalRatesMiniMatrixProps) {
  const {
    vehicle,
    basePriceNet,
    defaultMarginPct,
    wiborPct,
    marginPct,
    depreciationPct,
    initialDepositPct,
    replacementCar,
    gpsRequired,
    hookInstallation,
    tireClass,
    tireCountMode,
    tireCostCorrectionEnabled,
    tireCostCorrection,
    rimDiameter,
    serviceCostType,
    vehicleVintage,
    isMetalic,
    discountPct,
    factoryOptions,
    serviceOptions,
  } = props;

  // ── State ──────────────────────────────────────────────────────────────────
  const [sliderMargin, setSliderMargin] = useState<number>(defaultMarginPct);
  const [cells, setCells] = useState<MiniMatrixCell[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasCalculated, setHasCalculated] = useState(false);

  // Decision center state
  const [selectedCellKey, setSelectedCellKey] = useState<string | null>(null);
  const [budgetMax, setBudgetMax] = useState<number | null>(null);
  const [drillDownOpen, setDrillDownOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── API ────────────────────────────────────────────────────────────────────

  const fetchMatrix = useCallback(
    async (price: number, margin: number) => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      setError(null);

      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

      try {
        const promises = TARGET_KM_PER_YEAR.map((kmPerYear) => {
          const refMonths = 48;
          const przebiegBazowy = kmPerYear * (refMonths / 12);

          const payload = {
            vehicle_id: vehicle.id || "unknown",
            base_price_net: price,
            discount_pct: discountPct,
            factory_options: factoryOptions.map((o) => ({
              name: o.name,
              price_net: o.price_net,
              price_gross: o.price_net * 1.23,
              include_in_wr: false,
            })),
            service_options: serviceOptions.map((o) => ({
              name: o.name,
              price_net: o.price_net,
              price_gross: o.price_net * 1.23,
              include_in_wr: o.include_in_wr || false,
            })),
            okres_bazowy: refMonths,
            przebieg_bazowy: przebiegBazowy,
            pricing_margin_pct: margin,
            wibor_pct: wiborPct,
            margin_pct: marginPct,
            depreciation_pct: depreciationPct || null,
            initial_deposit_pct: initialDepositPct,
            replacement_car_enabled: replacementCar,
            add_gsm_subscription: gpsRequired,
            add_hook_installation: hookInstallation,
            z_oponami: true,
            klasa_opony_string: tireClass,
            srednica_felgi: rimDiameter,
            liczba_kompletow_opon:
              tireCountMode === "auto"
                ? null
                : parseFloat(tireCountMode) || null,
            korekta_kosztu_opon: tireCostCorrectionEnabled,
            koszt_opon_korekta: tireCostCorrection,
            service_cost_type: serviceCostType,
            vehicle_vintage: vehicleVintage,
            is_metalic: isMetalic,
            settings: { settings_version_id: null, overrides: null },
          };

          return fetch(`${baseUrl}/api/calculate-matrix`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller.signal,
          })
            .then((r) => {
              if (!r.ok) throw new Error(`API error ${r.status}`);
              return r.json();
            })
            .then((data) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const relevantCells: MiniMatrixCell[] = (data.cells || [])
                .filter(
                  (c: { months: number }) =>
                    TARGET_MONTHS.includes(c.months)
                )
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                .map((c: any) => ({
                  months: c.months,
                  km_per_year: kmPerYear,
                  total_km: c.total_km || kmPerYear * (c.months / 12),
                  price_net: c.price_net,
                  base_cost_net: c.base_cost_net || 0,
                  marza_mc: c.marza_mc || 0,
                  marza_na_kontrakcie: c.marza_na_kontrakcie || 0,
                  marza_na_kontrakcie_pct: c.marza_na_kontrakcie_pct || 0,
                  czynsz_finansowy: c.czynsz_finansowy || 0,
                  czynsz_techniczny: c.czynsz_techniczny || 0,
                  rv_samar_net: c.rv_samar_net || 0,
                  koszt_dzienny: c.koszt_dzienny || 0,
                  koszty_ogolem: c.koszty_ogolem || 0,
                  breakdown: c.breakdown || {
                    finance: { base: 0, margin: 0, price: 0 },
                    technical: {
                      service: { base: 0, margin: 0, price: 0 },
                      tires: { base: 0, margin: 0, price: 0 },
                      insurance: { base: 0, margin: 0, price: 0 },
                      replacement_car: { base: 0, margin: 0, price: 0 },
                      additional_costs: { base: 0, margin: 0, price: 0 },
                    },
                  },
                  status: c.status,
                }));
              return relevantCells;
            });
        });

        const results = await Promise.all(promises);
        if (controller.signal.aborted) return;

        const allCells = results.flat();
        setCells(allCells);
        setHasCalculated(true);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        console.error("Mini-matrix calc error:", err);
        setError(
          err instanceof Error ? err.message : "Błąd kalkulacji"
        );
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    },
    [
      vehicle.id,
      discountPct,
      wiborPct,
      marginPct,
      depreciationPct,
      initialDepositPct,
      replacementCar,
      gpsRequired,
      hookInstallation,
      tireClass,
      tireCountMode,
      tireCostCorrectionEnabled,
      tireCostCorrection,
      rimDiameter,
      serviceCostType,
      vehicleVintage,
      isMetalic,
      factoryOptions,
      serviceOptions,
    ]
  );

  const triggerCalc = useCallback(
    (price: number, margin: number) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (price <= 0) return;
      debounceRef.current = setTimeout(() => {
        fetchMatrix(price, margin);
      }, DEBOUNCE_MS);
    },
    [fetchMatrix]
  );

  const handleSliderChange = (val: number) => {
    setSliderMargin(val);
    if (basePriceNet > 0) {
      triggerCalc(basePriceNet, val);
    }
  };

  // Auto-trigger on mount
  useEffect(() => {
    if (basePriceNet > 0 && !hasCalculated) {
      triggerCalc(basePriceNet, sliderMargin);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basePriceNet]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  // ── Derived ────────────────────────────────────────────────────────────────

  const priceRange = useMemo(() => {
    if (cells.length === 0) return { min: 0, max: 10000 };
    const prices = cells.map((c) => c.price_net);
    return {
      min: Math.floor(Math.min(...prices) / 100) * 100,
      max: Math.ceil(Math.max(...prices) / 100) * 100,
    };
  }, [cells]);

  const selectedCell = useMemo(() => {
    if (!selectedCellKey) return null;
    return cells.find(
      (c) => `${c.months}_${c.km_per_year}` === selectedCellKey
    ) || null;
  }, [cells, selectedCellKey]);

  const canCalc = basePriceNet > 0;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="border border-slate-200 rounded-xl bg-white mt-4 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white">
        <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-600">
          <LayoutDashboard className="w-4 h-4 mr-2 text-blue-500" />
          Centrum Decyzyjne
        </h4>
      </div>

      <div className="p-5">
        {/* Margin slider */}
        <div className="mb-5">
          <label className="block text-xs font-bold uppercase text-slate-500 mb-1.5">
            Marża sprzedaży LTR:{" "}
            <span className="text-blue-700 text-sm font-black">
              {sliderMargin.toFixed(1)}%
            </span>
          </label>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-slate-400 font-semibold tabular-nums">
              0%
            </span>
            <input
              type="range"
              min={0}
              max={30}
              step={0.5}
              value={sliderMargin}
              onChange={(e) =>
                handleSliderChange(parseFloat(e.target.value))
              }
              className="flex-1 h-2 bg-slate-200 rounded-full appearance-none cursor-pointer accent-blue-600
                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white
                [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white [&::-moz-range-thumb]:cursor-pointer"
            />
            <span className="text-[10px] text-slate-400 font-semibold tabular-nums">
              30%
            </span>
          </div>
        </div>

        {/* Content area */}
        <div className="relative min-h-[120px]">
          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-[2px] flex items-center justify-center rounded-xl">
              <div className="flex items-center text-blue-600 bg-white px-5 py-2.5 rounded-full shadow-md border border-blue-100">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                <span className="text-xs font-semibold">
                  Kalkuluję stawki…
                </span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="text-center py-8">
              <p className="text-xs text-red-600 font-medium mb-3">
                {error}
              </p>
              <button
                onClick={() => {
                  if (canCalc) fetchMatrix(basePriceNet, sliderMargin);
                }}
                className="text-xs font-semibold px-4 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition-colors border border-red-200"
              >
                Spróbuj ponownie
              </button>
            </div>
          )}

          {/* Empty state */}
          {!hasCalculated && !isLoading && !error && (
            <div className="text-center py-12 text-slate-400 text-xs">
              Stawki zostaną obliczone automatycznie gdy dane pojazdu są dostępne.
            </div>
          )}

          {/* ── Decision Center Content ── */}
          {hasCalculated && cells.length > 0 && !error && (
            <>
              {/* 0. Sticky Context Header */}
              <StickyContextHeader
                brand={vehicle.brand || ""}
                model={vehicle.model || ""}
                basePriceNet={basePriceNet}
                baseMonths={48}
                baseKmTotal={48 / 12 * 40000}
              />

              {/* 1. KPI Badges */}
              <DecisionCenterKPI
                cells={cells}
                selectedCell={selectedCell}
                tireClass={tireClass}
                budgetMax={budgetMax}
              />

              {/* 2. Budget Filter */}
              <BudgetFilter
                priceMin={priceRange.min}
                priceMax={priceRange.max}
                budgetMax={budgetMax}
                onBudgetChange={setBudgetMax}
              />

              {/* 3. Heatmap Matrix */}
              <HeatmapMatrix
                cells={cells}
                targetMonths={TARGET_MONTHS}
                targetKmPerYear={TARGET_KM_PER_YEAR}
                selectedKey={selectedCellKey}
                onCellSelect={setSelectedCellKey}
                budgetMax={budgetMax}
              />

              {/* 4. Explore Matrix Button (when cell selected) */}
              {selectedCell && (
                <div className="mt-3">
                  <ExploreMatrixButton
                    isExpanded={drillDownOpen}
                    onToggle={() => setDrillDownOpen((p) => !p)}
                  />
                </div>
              )}

              {/* 5. Cost Breakdown Panel (when cell selected & drill-down open) */}
              {selectedCell && drillDownOpen && (
                <CostBreakdownPanel cell={selectedCell} />
              )}

              {/* 6. Ranking List */}
              <RankingList cells={cells} budgetMax={budgetMax} />

              {/* Footnote */}
              <p className="text-[10px] text-slate-400 mt-4 text-right">
                Stawki łączne netto/mc • marża {sliderMargin.toFixed(1)}%
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
