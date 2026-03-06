import { useState, useEffect, useRef, useCallback } from "react";
import { Loader2, TrendingUp } from "lucide-react";
import type { FleetVehicleView } from "../../types";

// ── Types ────────────────────────────────────────────────────────────────────

interface MiniMatrixCell {
  months: number;
  km_per_year: number;
  price_net: number;
  status: string;
}

interface RentalRatesMiniMatrixProps {
  vehicle: FleetVehicleView;
  basePriceNet: number;
  defaultMarginPct: number;
  // Calculator params needed for API payload
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
  // Options for WR
  factoryOptions: { name: string; price_net: number; no_discount?: boolean; include_in_wr?: boolean }[];
  serviceOptions: { name: string; price_net: number; include_in_wr?: boolean }[];
}

// ── Constants ────────────────────────────────────────────────────────────────

const TARGET_MONTHS = [36, 48, 60];
const TARGET_KM_PER_YEAR = [30000, 40000, 50000, 60000];
const DEBOUNCE_MS = 600;

// ── Helper ───────────────────────────────────────────────────────────────────

function fmtPLN(val: number): string {
  return val.toLocaleString("pl-PL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

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

  // Local state
  const [sliderMargin, setSliderMargin] = useState<number>(defaultMarginPct);
  const [cells, setCells] = useState<MiniMatrixCell[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasCalculated, setHasCalculated] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Build and fire API calls
  const fetchMatrix = useCallback(
    async (price: number, margin: number) => {
      // Cancel any in-flight request
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      setError(null);

      const baseUrl =
        import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

      try {
        // 4 parallel calls — one per km/year target
        const promises = TARGET_KM_PER_YEAR.map((kmPerYear) => {
          const refMonths = 48; // reference period for ratio
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
              // Filter to only TARGET_MONTHS cells
              const relevantCells: MiniMatrixCell[] = (
                data.cells || []
              )
                .filter(
                  (c: { months: number }) =>
                    TARGET_MONTHS.includes(c.months)
                )
                .map(
                  (c: {
                    months: number;
                    km_per_year: number;
                    price_net: number;
                    status: string;
                  }) => ({
                    months: c.months,
                    km_per_year: kmPerYear,
                    price_net: c.price_net,
                    status: c.status,
                  })
                );
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

  // Debounced trigger on slider change
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

  // Slider change handler
  const handleSliderChange = (val: number) => {
    setSliderMargin(val);
    if (basePriceNet > 0) {
      triggerCalc(basePriceNet, val);
    }
  };

  // Auto-trigger on mount when price is available
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

  // ── Build matrix table data ──

  // Map: months → km_per_year → price_net
  const cellMap = new Map<string, MiniMatrixCell>();
  for (const c of cells) {
    cellMap.set(`${c.months}_${c.km_per_year}`, c);
  }

  const canCalc = basePriceNet > 0;

  return (
    <div className="border border-slate-200 rounded bg-white mt-4 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
        <h4 className="flex items-center text-xs font-semibold uppercase tracking-wider text-slate-500">
          <TrendingUp className="w-4 h-4 mr-2 text-slate-400" />
          Stawki najmu — podgląd
        </h4>
      </div>

      <div className="p-5">
        {/* Controls row */}
        <div className="flex flex-wrap items-end gap-6 mb-5">
          {/* Margin slider */}
          <div className="flex-1 min-w-[260px]">
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
              Marża sprzedaży LTR:{" "}
              <span className="text-blue-700 text-sm font-bold">
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
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer"
              />
              <span className="text-[10px] text-slate-400 font-semibold tabular-nums">
                30%
              </span>
            </div>
          </div>
        </div>

        {/* Matrix table area */}
        <div className="relative min-h-[120px]">
          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute inset-0 z-10 bg-white/70 backdrop-blur-[1px] flex items-center justify-center rounded">
              <div className="flex items-center text-blue-600 bg-white px-4 py-2 rounded-full shadow-sm border border-blue-100">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                <span className="text-xs font-medium">
                  Kalkuluję stawki…
                </span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="text-center py-6">
              <p className="text-xs text-red-600 font-medium mb-2">
                {error}
              </p>
              <button
                onClick={() => {
                  if (canCalc) fetchMatrix(basePriceNet, sliderMargin);
                }}
                className="text-xs font-semibold px-3 py-1.5 rounded bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
              >
                Spróbuj ponownie
              </button>
            </div>
          )}

          {/* Empty state */}
          {!hasCalculated && !isLoading && !error && (
            <div className="text-center py-8 text-slate-400 text-xs">
              Stawki zostaną obliczone automatycznie gdy dane pojazdu są dostępne.
            </div>
          )}

          {/* Results table */}
          {hasCalculated && cells.length > 0 && !error && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="py-2 text-left text-xs font-bold uppercase text-slate-400 w-24">
                    Okres
                  </th>
                  {TARGET_KM_PER_YEAR.map((km) => (
                    <th
                      key={km}
                      className="py-2 text-center text-xs font-bold uppercase text-slate-400"
                    >
                      {km / 1000}k km/rok
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {TARGET_MONTHS.map((months) => (
                  <tr
                    key={months}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-3 text-xs font-semibold text-slate-600">
                      {months} mc
                    </td>
                    {TARGET_KM_PER_YEAR.map((km) => {
                      const cell = cellMap.get(`${months}_${km}`);
                      return (
                        <td
                          key={km}
                          className="py-3 text-center tabular-nums"
                        >
                          {cell ? (
                            <span className="text-sm font-bold text-blue-700">
                              {fmtPLN(cell.price_net)}
                              <span className="text-[9px] text-slate-400 font-normal ml-0.5">
                                PLN
                              </span>
                            </span>
                          ) : (
                            <span className="text-xs text-slate-300">
                              —
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footnote */}
        {hasCalculated && cells.length > 0 && !error && (
          <p className="text-[10px] text-slate-400 mt-3 text-right">
            Stawki łączne netto/mc • marża {sliderMargin.toFixed(1)}%
          </p>
        )}
      </div>
    </div>
  );
}
