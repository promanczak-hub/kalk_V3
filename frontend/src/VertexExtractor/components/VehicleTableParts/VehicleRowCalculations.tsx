import { useState, useEffect } from "react";
import {
  Box,
  Typography,
} from "@mui/material";
import { Calculator, ChevronDown, ChevronUp, Loader2, FileCode2, RotateCcw, X, Settings, TrendingUp } from "lucide-react";
import { MatrixFilterToolbar } from "../../../CalculatorPanel/MatrixFilterToolbar";
import { ReversePriceLookup } from "../../../CalculatorPanel/ReversePriceLookup";
import { MatrixHeatmapView, MatrixViewToggle } from "../../../CalculatorPanel/MatrixHeatmapView";

import { fmtPLN } from "./calculations/calculations.utils";
import { CellDetail } from "./calculations/CellDetail";
import { useVehicleCalculations } from "./calculations/useVehicleCalculations";

export function VehicleRowCalculations({ 
  kalkulacjaId, 
  kalkulacjaNumer,
  vehicleId,
  vehicleName = "",
  powertrain = "",
  offerNumber = "",
  configCode = "",
  basePrice = 0,
  onBestPriceFound,
  onSpecificPriceFound
}: { 
  kalkulacjaId: string; 
  kalkulacjaNumer: string;
  vehicleId: string;
  vehicleName?: string;
  powertrain?: string;
  offerNumber?: string;
  configCode?: string;
  basePrice?: number;
  onBestPriceFound?: (price: number | null) => void;
  onSpecificPriceFound?: (price: number | null) => void;
}) {
  const [matrixView, setMatrixView] = useState<"cards" | "heatmap">("heatmap");
  const [expandedCell, setExpandedCell] = useState<string | null>(null);

  const {
    cells,
    filteredCells,
    loading,
    error,
    traceData,
    setTraceData,
    recalculating,
    fetchingTraceCell,
    marginRecalculating,
    basePayload,
    filters,
    setFilters,
    mileageMode,
    setMileageMode,
    mileageReferenceMonths,
    isGlobalRecalculating,
    globalWrCorrection,
    setGlobalWrCorrection,
    globalTireCorrection,
    setGlobalTireCorrection,
    modifiedCells,
    getOverrides,
    fetchMatrix,
    handleOverridesChange,
    recalculateSingleCell,
    resetCell,
    fetchTraceSingleCell,
    handleExactRecalculate,
    handleGlobalRecalculate,
    recalculateWithMargin
  } = useVehicleCalculations({
    kalkulacjaId,
    vehicleId,
    onBestPriceFound,
    onSpecificPriceFound
  });

  useEffect(() => {
    fetchMatrix();
  }, [fetchMatrix]);

  if (!kalkulacjaId) {
    return (
      <Box sx={{ p: 6, textAlign: "center" }}>
        <Typography variant="h6" color="text.secondary">
          Wybierz kalkulację z listy lub utwórz nową w Vertex Extractor.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 4, pt: 4, borderTop: "1px dashed #cbd5e1", backgroundColor: "transparent" }}>
      {/* Top Banner */}
      <Box sx={{ p: 2, mb: 2, bgcolor: "transparent" }}>
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <Calculator className="w-6 h-6 text-blue-700" />
              <div>
                <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2 }}>
                  Kalkulacja: {kalkulacjaNumer}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  ID: {kalkulacjaId}
                </Typography>
              </div>
            </div>
            {/* Added context details */}
            {(offerNumber || configCode || vehicleName) && (
              <div className="flex flex-wrap items-center gap-2 mt-1 pl-9 text-xs text-slate-500 font-medium">
                {offerNumber && (
                  <span className="border border-slate-200 bg-white px-1.5 py-0.5 rounded shadow-sm">Oferta: {offerNumber}</span>
                )}
                {configCode && (
                  <span className="border border-slate-200 bg-white px-1.5 py-0.5 rounded shadow-sm">Kod: {configCode}</span>
                )}
                {vehicleName && (
                  <span className="text-slate-600 ml-1">
                    {vehicleName} {powertrain && `• ${powertrain}`} 
                    {basePrice > 0 && ` • ${fmtPLN(basePrice)} PLN netto`}
                  </span>
                )}
              </div>
            )}
          </div>
            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-2">
                {modifiedCells.size > 0 && (
                  <span className="text-[10px] text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded">
                    {modifiedCells.size} zmodyfikowana(e)
                  </span>
                )}
                <button
                  onClick={fetchMatrix}
                  className="flex items-center text-xs font-semibold px-3 py-1.5 rounded bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 transition-colors shadow-sm"
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                  Reset (odśwież z serwera)
                </button>
              </div>
              
              <div className="flex items-center gap-4 mt-1 bg-slate-50/50 p-2 rounded-lg border border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">🔧 Korekta: WR</span>
                  <input
                    type="number"
                    step={500}
                    value={globalWrCorrection}
                    onChange={(e) => { const parsed = parseFloat(e.target.value); setGlobalWrCorrection(isNaN(parsed) ? globalWrCorrection : parsed); }}
                    className="w-20 text-xs p-1 border border-slate-200 rounded text-right outline-none focus:ring-1 focus:ring-blue-400 tabular-nums bg-white shadow-sm"
                    placeholder="WR"
                  />
                  <span className="text-[10px] text-slate-400">PLN</span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">🛞 Korekta: Opony</span>
                  <input
                    type="number"
                    step={200}
                    value={globalTireCorrection}
                    onChange={(e) => { const parsed = parseFloat(e.target.value); setGlobalTireCorrection(isNaN(parsed) ? globalTireCorrection : parsed); }}
                    className="w-20 text-xs p-1 border border-slate-200 rounded text-right outline-none focus:ring-1 focus:ring-blue-400 tabular-nums bg-white shadow-sm"
                    placeholder="Opony"
                  />
                  <span className="text-[10px] text-slate-400">PLN</span>
                </div>

                <button
                  onClick={handleGlobalRecalculate}
                  disabled={isGlobalRecalculating || loading}
                  className="flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 transition-all disabled:opacity-50 shadow-md uppercase tracking-wide"
                >
                  {isGlobalRecalculating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <TrendingUp className="w-3.5 h-3.5" />}
                  Przelicz Korekty
                </button>
              </div>
            </div>
        </div>
      </Box>

      {/* Main content */}
      <Box sx={{ px: 0, width: "100%" }}>
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500 bg-slate-50/50 rounded-xl border border-slate-100">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-slate-700">Trwa obliczanie matrycy LTR...</h3>
            <p className="text-xs text-slate-400 mt-1">Proszę czekać, pobieram najnowsze stawki</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <Typography variant="body2" color="error" sx={{ fontWeight: "bold" }}>
              Błąd: {error}
            </Typography>
            <button
              onClick={fetchMatrix}
              className="mt-2 text-xs font-semibold px-4 py-1.5 rounded bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
            >
              Spróbuj ponownie
            </button>
          </div>
        )}

        {!loading && !error && cells.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="flex items-center text-sm font-bold uppercase tracking-wider text-slate-500">
                <Calculator className="w-4 h-4 mr-2" />
                Matryca rat LTR ({filteredCells.length} / {cells.length} wariantów)
              </h3>
              <MatrixViewToggle view={matrixView} onViewChange={setMatrixView} />
            </div>

            {/* Matrix filter toolbar */}
            <MatrixFilterToolbar
              defaultMarginPct={basePayload?.pricing_margin_pct ?? null}
              filters={filters}
              mileageMode={mileageMode}
              onMileageModeChange={setMileageMode}
              referenceMonths={mileageReferenceMonths}
              onFiltersChange={setFilters}
              onMarginRecalculate={recalculateWithMargin}
              onExactRecalculate={handleExactRecalculate}
              isRecalculating={marginRecalculating}
            />

            {/* Reverse price lookup */}
            <ReversePriceLookup basePayload={basePayload} vehicleId={vehicleId} />

            {/* Data quality warnings */}
            {cells.some(c => c.warnings?.service_fallback_used) && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 mb-3 flex items-center gap-2">
                <span className="text-amber-600 text-sm">⚠️</span>
                <span className="text-xs text-amber-800 font-medium">
                  Brak stawek serwisowych SAMAR dla tego pojazdu — koszt serwisu = 0 PLN. Uzupełnij dane w Control Center.
                </span>
              </div>
            )}
            {cells.some(c => c.warnings?.replacement_car_missing) && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 mb-3 flex items-center gap-2">
                <span className="text-amber-600 text-sm">⚠️</span>
                <span className="text-xs text-amber-800 font-medium">
                  Brak danych auta zastępczego dla tej klasy SAMAR — koszt = 0 PLN. Sprawdź mapowanie klasy WR → SAMAR.
                </span>
              </div>
            )}

            {/* Matrix View: Heatmap or Cards */}
            {matrixView === "heatmap" ? (
              <MatrixHeatmapView 
                cells={filteredCells} 
                mileageMode={mileageMode} 
                onShowTrace={(cell) => fetchTraceSingleCell(cell.Okres, cell.Przebieg)}
                isFetchingTrace={fetchingTraceCell !== null}
              />
            ) : (
            /* Matrix Card Grid */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {filteredCells.map((cell) => {
                const cellKey = `${cell.Okres}-${cell.Przebieg}`;
                const isExpanded = expandedCell === cellKey;
                const isMod = modifiedCells.has(cell.Okres);

                return (
                  <div key={cellKey} className={isExpanded ? "sm:col-span-2 lg:col-span-3 xl:col-span-4" : ""}>
                    {/* Matrix Cell Card */}
                    <button
                      onClick={() => setExpandedCell(isExpanded ? null : cellKey)}
                      className={`w-full text-left p-3 rounded-lg border transition-all cursor-pointer hover:shadow-md ${
                        isExpanded
                          ? "bg-blue-50 border-blue-300 shadow-md"
                          : isMod
                            ? "bg-blue-50/50 border-blue-200 hover:border-blue-400 ring-1 ring-blue-100"
                            : cell.status === "OK"
                              ? "bg-white border-slate-200 hover:border-blue-300"
                              : "bg-amber-50/50 border-amber-200 hover:border-amber-400"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <div className="text-xs font-bold text-slate-400 uppercase">
                              {cell.Okres} miesięcy
                            </div>
                            {isMod && <Settings className="w-3 h-3 text-blue-500" />}
                          </div>
                          <div className="text-xs text-slate-400">
                            {mileageMode === "contract"
                              ? `${((cell.PrzebiegKontrakt ?? ((cell.Okres / 12) * cell.Przebieg)) / 1000).toFixed(0)}k km/kontrakt`
                              : `${((cell.PrzebiegKontrakt ?? ((cell.Okres / 12) * cell.Przebieg)) / 1000).toFixed(0)}k km (${cell.Przebieg.toLocaleString("pl-PL")} km/rok)`}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-right">
                            <div className="text-sm font-bold text-blue-700 tabular-nums">
                              {fmtPLN(cell.LacznaStawka)}
                            </div>
                            <div className="text-[9px] text-slate-400">PLN netto/mc</div>
                          </div>
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      </div>
                    </button>

                    {/* Expanded Detail with Expert Mode */}
                    {isExpanded && (
                      <CellDetail
                        cell={cell}
                        overrides={getOverrides(cell.Okres)}
                        isModified={isMod}
                        isRecalculating={recalculating === cell.Okres}
                        isFetchingTrace={fetchingTraceCell === cell.Okres}
                        onOverridesChange={(o) => handleOverridesChange(cell.Okres, o)}
                        onRecalculate={() => recalculateSingleCell(cell.Okres)}
                        onReset={() => resetCell(cell.Okres)}
                        onShowTrace={() => fetchTraceSingleCell(cell.Okres)}
                      />
                    )}
                  </div>
                );
              })}
            </div>
            )}
          </div>
        )}

        {!loading && !error && cells.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <Calculator className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <Typography variant="body1">Brak wyników matrycy</Typography>
            <Typography variant="body2" color="text.secondary">
              Sprawdź dane wejściowe na karcie pojazdu w Vertex Extractor.
            </Typography>
          </div>
        )}

        {/* Trace Modal */}
        {traceData && (
          <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
                <div className="flex items-center gap-3">
                  <FileCode2 className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-bold text-slate-800 text-lg">Ślad Diagnostyczny (V3 Calculation Trace)</h3>
                </div>
                <button
                  onClick={() => setTraceData(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
                {traceData.length > 0 ? (
                  <div className="space-y-3">
                    {traceData.map((t, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-start gap-4 mb-2">
                          <div className="font-bold text-slate-700 text-sm">
                            <span className="text-slate-400 font-mono text-xs mr-2">[{idx + 1}]</span>
                            {t.krok}
                          </div>
                          <div className="font-mono text-sm font-bold text-blue-700 shrink-0 tabular-nums">
                            {typeof t.wynik === 'number' ? fmtPLN(t.wynik) : String(t.wynik)}
                          </div>
                        </div>
                        {t.rownanie && (
                          <div className="text-xs text-slate-500 font-mono bg-slate-50 p-2 rounded border border-slate-100">
                            {t.rownanie}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-10 text-slate-400">
                    Brak śladu dla tej kalkulacji.
                  </div>
                )}
              </div>
              
            </div>
          </div>
        )}
      </Box>
    </Box>
  );
}
