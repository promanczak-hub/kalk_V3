import { Search, X, Loader2, Car } from "lucide-react";
import { SearchFilter, SearchResult } from "../types";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function ReverseSearchResults({ state, actions }: { state: any; actions: any }) {
  const { activeFilters, hasSearched, searching, results, totalCount, priceMonths, priceMileage, priceMarginPct } = state;
  const { setActiveFilters } = actions;

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
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center animate-in fade-in duration-200">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-4">
            <Car className="w-7 h-7 text-amber-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-600 mb-1">
            Brak wyników
          </h3>
          <p className="text-xs text-slate-400">
            Żaden pojazd nie spełnia wszystkich wybranych kryteriów.
            Spróbuj usunąć część filtrów.
          </p>
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
            {searching && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-500" />}
          </div>

          {results.map((r: SearchResult) => (
            <div
              key={r.source_vehicle_id}
              className="bg-white border border-slate-200 rounded-lg p-4 hover:border-indigo-200 hover:shadow-sm transition-all flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                  <Car className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700">
                    {r.brand || "—"} {r.model || ""}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    {r.source_vehicle_id.slice(0, 8)}...
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-xs font-bold text-emerald-600">
                    {r.matched_features}/{r.total_filters} trafień
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {Math.round(r.match_score * 100)}% dopasowania
                  </div>
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
                      r.match_score >= 0.8
                        ? "#059669, #34d399"
                        : r.match_score >= 0.5
                        ? "#d97706, #fbbf24"
                        : "#dc2626, #f87171"
                    })`,
                  }}
                >
                  {Math.round(r.match_score * 100)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
