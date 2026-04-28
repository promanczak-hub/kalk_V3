import { useState } from "react";
import { Search, X, Loader2, Car, Check, GitCompareArrows, Sparkles, ArrowRight } from "lucide-react";
import type { CatalogCategory, SearchFilter, SearchResult } from "../types";
import { VehicleComparisonModal } from "./VehicleComparisonModal";
import { useRelaxSuggestions } from "../hooks/useRelaxSuggestions";

const MAX_CHIPS_PER_KIND = 5;
const MAX_COMPARE = 4;

function buildNameLookup(catalog: CatalogCategory[]): Record<string, string> {
  const map: Record<string, string> = {};
  catalog.forEach((c) => {
    c.features.forEach((f) => {
      map[f.feature_key] = f.display_name;
    });
  });
  return map;
}

function MatchChips({
  matched,
  missing,
  nameLookup,
}: {
  matched: string[];
  missing: string[];
  nameLookup: Record<string, string>;
}) {
  if (matched.length === 0 && missing.length === 0) return null;
  const matchedHead = matched.slice(0, MAX_CHIPS_PER_KIND);
  const missingHead = missing.slice(0, MAX_CHIPS_PER_KIND);
  const matchedRest = matched.length - matchedHead.length;
  const missingRest = missing.length - missingHead.length;

  return (
    <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-1">
      {matchedHead.map((k) => (
        <span
          key={`m-${k}`}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-100"
          title={nameLookup[k] || k}
        >
          <Check className="w-2.5 h-2.5" />
          {nameLookup[k] || k}
        </span>
      ))}
      {matchedRest > 0 && (
        <span className="text-[10px] text-emerald-600 font-medium px-1 py-0.5">
          +{matchedRest}
        </span>
      )}
      {missingHead.map((k) => (
        <span
          key={`x-${k}`}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-50 text-rose-700 border border-rose-100 line-through decoration-rose-300"
          title={`Brakuje: ${nameLookup[k] || k}`}
        >
          <X className="w-2.5 h-2.5 no-underline" />
          {nameLookup[k] || k}
        </span>
      ))}
      {missingRest > 0 && (
        <span className="text-[10px] text-rose-600 font-medium px-1 py-0.5">
          +{missingRest}
        </span>
      )}
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function ReverseSearchResults({ state, actions }: { state: any; actions: any }) {
  const {
    activeFilters,
    hasSearched,
    searching,
    results,
    totalCount,
    priceMonths,
    priceMileage,
    priceMarginPct,
    catalog,
    globalSearchQuery,
    bodyTypes,
    vehicleScope,
    priceMin,
    priceMax,
    priceDepositPct,
  } = state;
  const {
    setActiveFilters,
    setBodyTypes,
    setVehicleScope,
    setPriceMin,
    setPriceMax,
  } = actions;

  const nameLookup = buildNameLookup(catalog || []);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showComparison, setShowComparison] = useState(false);

  const relax = useRelaxSuggestions();

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < MAX_COMPARE) {
        next.add(id);
      }
      return next;
    });
  };

  const selectedVehicles = (results as SearchResult[])
    .filter((r) => selectedIds.has(r.source_vehicle_id || r.vehicle_id))
    .map((r) => ({
      id: r.source_vehicle_id || r.vehicle_id,
      brand: r.brand ?? null,
      model: r.model ?? null,
    }));

  return (
    <div className="flex-1 min-w-0">
      {/* Active filters bar */}
      {activeFilters.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {activeFilters.map((f: SearchFilter) => (
            <span
              key={f.feature_key}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"
            >
              {f.display_name}
              <button
                onClick={() =>
                  setActiveFilters((prev: SearchFilter[]) =>
                    prev.filter((af) => af.feature_key !== f.feature_key)
                  )
                }
                className="ml-0.5 hover:text-red-500"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Results */}
      {!hasSearched && (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <Search className="w-7 h-7 text-slate-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-600 mb-1">
            Wybierz cechy i uruchom wyszukiwanie
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Rozwiń kategorię po lewej stronie, zaznacz wymagane cechy,
            a następnie kliknij &quot;Szukaj&quot;.
          </p>
        </div>
      )}

      {searching && results.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" />
          <span className="text-sm text-slate-500">Przeszukuję bazę pojazdów...</span>
        </div>
      )}

      {hasSearched && !searching && results.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-8 text-center animate-in fade-in duration-200">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-4">
            <Car className="w-7 h-7 text-amber-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-600 mb-1">
            Brak dopasowań
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
            Żaden pojazd w bazie nie spełnia wszystkich wybranych kryteriów.
          </p>
          {activeFilters.length > 0 ? (
            <div className="max-w-lg mx-auto text-left">
              <p className="text-[11px] text-slate-500 mb-2 font-medium">
                Kliknij ✗ aby usunąć cechę i poszerzyć wyszukiwanie:
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                {activeFilters.map((f: SearchFilter) => (
                  <button
                    key={`empty-${f.feature_key}`}
                    onClick={() =>
                      setActiveFilters((prev: SearchFilter[]) =>
                        prev.filter((af) => af.feature_key !== f.feature_key)
                      )
                    }
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 hover:border-rose-300 transition-colors group"
                    title={`Usuń wymaganie: ${f.display_name}`}
                  >
                    {f.display_name}
                    <X className="w-3 h-3 group-hover:scale-125 transition-transform" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[11px] text-slate-400">
              Spróbuj zmienić zakres pojazdów lub poszerzyć kryteria.
            </p>
          )}

          {/* Relax suggestions */}
          <div className="mt-6 pt-5 border-t border-slate-100 max-w-lg mx-auto">
            {relax.suggestions.length === 0 && !relax.loading && (
              <button
                type="button"
                onClick={() =>
                  relax.compute({
                    globalSearchQuery,
                    activeFilters,
                    bodyTypes,
                    vehicleScope,
                    priceMin,
                    priceMax,
                    priceMonths,
                    priceMileage,
                    priceDepositPct,
                    setActiveFilters: (next: SearchFilter[]) => setActiveFilters(next),
                    setBodyTypes: (next: string[]) => setBodyTypes(next),
                    setVehicleScope: (next: "all" | "passenger" | "commercial") =>
                      setVehicleScope(next),
                    setPriceMin: (next: number | "") => setPriceMin(next),
                    setPriceMax: (next: number | "") => setPriceMax(next),
                  })
                }
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors"
              >
                <Sparkles className="w-3 h-3" />
                Sprawdź które filtry najmocniej zawężają
              </button>
            )}

            {relax.loading && (
              <div className="flex items-center justify-center gap-2 text-[11px] text-indigo-600">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Analizuję...
              </div>
            )}

            {!relax.loading && relax.suggestions.length > 0 && (
              <div>
                <p className="text-[11px] text-slate-500 mb-2 font-medium text-left">
                  Usuń jeden z poniższych aby odblokować wyniki:
                </p>
                <ul className="space-y-1">
                  {relax.suggestions.slice(0, 6).map((s) => (
                    <li key={`${s.kind}-${s.id}`}>
                      <button
                        type="button"
                        onClick={() => {
                          s.remove();
                          relax.reset();
                        }}
                        className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-md bg-white border border-slate-200 hover:border-emerald-400 hover:bg-emerald-50 transition-colors group"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-emerald-600 flex-shrink-0" />
                          <span className="text-xs text-slate-700 truncate text-left">
                            {s.label}
                          </span>
                        </div>
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded flex-shrink-0">
                          +{s.wouldUnlockCount}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                <button
                  type="button"
                  onClick={relax.reset}
                  className="mt-2 text-[10px] text-slate-400 hover:text-slate-600"
                >
                  Schowaj propozycje
                </button>
              </div>
            )}

            {!relax.loading && relax.error && (
              <div className="text-[11px] text-rose-600">{relax.error}</div>
            )}
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className={`space-y-3 transition-all duration-300 ${searching ? "opacity-40 pointer-events-none" : "opacity-100"}`}>
          <div className="text-xs text-slate-500 mb-2 flex items-center justify-between">
            <div>
              Znaleziono <span className="font-bold text-slate-700">{totalCount}</span> pojazdów
              {totalCount > results.length && (
                <span> (wyświetlono {results.length})</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {selectedIds.size >= 2 && (
                <button
                  onClick={() => setShowComparison(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors"
                >
                  <GitCompareArrows className="w-3 h-3" />
                  Porównaj {selectedIds.size}
                </button>
              )}
              {selectedIds.size > 0 && selectedIds.size < 2 && (
                <span className="text-[10px] text-slate-400">
                  Zaznacz 2-{MAX_COMPARE} pojazdy do porównania
                </span>
              )}
              {selectedIds.size > 0 && (
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="text-[10px] text-slate-500 hover:text-slate-700"
                  title="Wyczyść zaznaczenie"
                >
                  Wyczyść
                </button>
              )}
              {searching && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-500" />}
            </div>
          </div>

          {results.map((r: SearchResult) => {
            const matched = r.matched_feature_keys || [];
            const missing = r.missing_feature_keys || [];
            const matchedCount = r.matched_features ?? matched.length;
            const totalFilters = r.total_filters ?? matched.length + missing.length;
            const score = r.match_score ?? r.score ?? 0;
            const vehicleId = r.source_vehicle_id || r.vehicle_id;

            const isSelected = selectedIds.has(vehicleId);
            const canSelect = isSelected || selectedIds.size < MAX_COMPARE;

            return (
              <div
                key={vehicleId}
                className={`bg-white border rounded-lg p-4 hover:shadow-sm transition-all ${
                  isSelected ? "border-blue-400 ring-1 ring-blue-200" : "border-slate-200 hover:border-indigo-200"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={!canSelect}
                      onChange={() => toggleSelected(vehicleId)}
                      className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      title={
                        canSelect
                          ? "Zaznacz do porównania"
                          : `Zaznaczono już max ${MAX_COMPARE} pojazdy`
                      }
                    />
                    <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                      <Car className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-slate-700">
                        {r.brand || "—"} {r.model || ""}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        {vehicleId.slice(0, 8)}...
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-xs font-bold text-emerald-600">
                        {matchedCount}/{totalFilters} trafień
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {Math.round(score * 100)}% dopasowania
                      </div>
                      {(r.score_features_pct !== undefined &&
                        r.score_features_pct !== null) ||
                      (r.score_semantic !== undefined && r.score_semantic !== null) ? (
                        <div
                          className="text-[9px] text-slate-400 font-mono mt-0.5"
                          title={`Score = features (max 100) + semantic (max 30), capped at 100. Tutaj: ${r.score_features_pct?.toFixed(0) ?? 0} + ${r.score_semantic?.toFixed(0) ?? 0}`}
                        >
                          F:{r.score_features_pct?.toFixed(0) ?? 0}
                          {r.score_semantic !== undefined &&
                          r.score_semantic !== null &&
                          r.score_semantic > 0
                            ? ` · S:${r.score_semantic.toFixed(0)}`
                            : ""}
                        </div>
                      ) : null}
                    </div>

                    {priceMarginPct !== "" ? (
                      r.price_netto !== undefined && r.price_netto !== null ? (
                        <div className="ml-2 pl-3 py-1 border-l border-slate-200 text-right">
                          <div className="text-sm font-bold text-slate-800">
                            {r.price_netto.toFixed(0)} <span className="text-[10px] font-normal text-slate-500">PLN/mc</span>
                          </div>
                          <div className="text-[9px] text-slate-400 font-bold uppercase tracking-tight mt-0.5">
                            {priceMonths} {priceMonths === 1 ? 'msc' : 'm-cy'} | {priceMileage / 1000}k | Marża: {priceMarginPct}%
                          </div>
                        </div>
                      ) : (
                        <div className="ml-2 pl-3 py-1 border-l border-slate-200 text-right">
                          <span className="text-xs text-slate-400">Brak ceny</span>
                        </div>
                      )
                    ) : (
                      <div className="ml-2 pl-3 py-1 border-l border-slate-200 flex flex-col items-end justify-center">
                        <span className="text-[10px] text-amber-600 font-bold leading-tight text-right w-24">
                          Ustal marżę<br/>aby poznać ratę
                        </span>
                      </div>
                    )}

                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold text-white ml-2"
                      style={{
                        background: `linear-gradient(135deg, ${
                          score >= 0.8
                            ? "#059669, #34d399"
                            : score >= 0.5
                            ? "#d97706, #fbbf24"
                            : "#dc2626, #f87171"
                        })`,
                      }}
                    >
                      {Math.round(score * 100)}
                    </div>
                  </div>
                </div>

                <MatchChips
                  matched={matched}
                  missing={missing}
                  nameLookup={nameLookup}
                />
              </div>
            );
          })}
        </div>
      )}

      {showComparison && selectedVehicles.length >= 2 && (
        <VehicleComparisonModal
          vehicles={selectedVehicles}
          onClose={() => setShowComparison(false)}
        />
      )}
    </div>
  );
}
