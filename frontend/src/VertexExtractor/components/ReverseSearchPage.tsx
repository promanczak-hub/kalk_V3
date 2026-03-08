import { useState, useEffect, useCallback } from "react";
import { Search, Filter, X, Loader2, Car, ChevronDown, ChevronRight } from "lucide-react";

/* ── Types ────────────────────────────────────────────────────── */

interface CatalogFeature {
  id: string;
  feature_key: string;
  display_name: string;
  feature_type: string;
  category_id: string;
}

interface CatalogCategory {
  id: string;
  category_key: string;
  display_name: string;
  features: CatalogFeature[];
}

interface SearchFilter {
  feature_key: string;
  display_name: string;
  value_bool?: boolean;
  value_num_min?: number;
  value_num_max?: number;
  value_text?: string;
}

interface SearchResult {
  source_vehicle_id: string;
  brand: string | null;
  model: string | null;
  matched_features: number;
  total_filters: number;
  match_score: number;
}

/* ── Component ────────────────────────────────────────────────── */

export function ReverseSearchPage() {
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [activeFilters, setActiveFilters] = useState<SearchFilter[]>([]);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());
  const [hasSearched, setHasSearched] = useState(false);

  const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

  // Fetch catalog
  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        const res = await fetch(`${baseUrl}/api/features/catalog`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setCatalog(
          data.categories.filter((c: CatalogCategory) => c.features.length > 0)
        );
      } catch (err) {
        console.error("Failed to fetch catalog:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchCatalog();
  }, [baseUrl]);

  // Toggle feature filter
  const toggleFilter = useCallback(
    (feature: CatalogFeature) => {
      setActiveFilters((prev) => {
        const exists = prev.find((f) => f.feature_key === feature.feature_key);
        if (exists) {
          return prev.filter((f) => f.feature_key !== feature.feature_key);
        }
        return [
          ...prev,
          {
            feature_key: feature.feature_key,
            display_name: feature.display_name,
            value_bool: feature.feature_type === "bool" ? true : undefined,
          },
        ];
      });
    },
    []
  );

  // Search
  const runSearch = useCallback(async () => {
    if (activeFilters.length === 0) return;
    setSearching(true);
    setHasSearched(true);
    try {
      const res = await fetch(`${baseUrl}/api/features/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filters: activeFilters.map((f) => ({
            feature_key: f.feature_key,
            value_bool: f.value_bool,
            value_num_min: f.value_num_min,
            value_num_max: f.value_num_max,
            value_text: f.value_text,
          })),
          limit: 50,
          offset: 0,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.results);
      setTotalCount(data.total_count);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  }, [activeFilters, baseUrl]);

  const clearFilters = () => {
    setActiveFilters([]);
    setResults([]);
    setTotalCount(0);
    setHasSearched(false);
  };

  const toggleCat = (catId: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) next.delete(catId);
      else next.add(catId);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        <span>Ładowanie katalogu cech...</span>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Search className="w-5 h-5 text-indigo-600" />
          Reverse Search — Wyszukiwanie po cechach
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Zaznacz wymagane cechy pojazdu, aby znaleźć pasujące oferty w bazie.
        </p>
      </div>

      <div className="flex gap-6">
        {/* ── Left: Filter Sidebar ── */}
        <div className="w-80 shrink-0">
          <div className="bg-white border border-slate-200 rounded-lg shadow-sm sticky top-4">
            {/* Filter header */}
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 rounded-t-lg flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5" />
                Filtry cech
              </h3>
              {activeFilters.length > 0 && (
                <button
                  onClick={clearFilters}
                  className="text-[10px] text-red-500 hover:text-red-700 font-medium flex items-center gap-0.5"
                >
                  <X className="w-3 h-3" />
                  Wyczyść ({activeFilters.length})
                </button>
              )}
            </div>

            {/* Category list */}
            <div className="max-h-[calc(100vh-240px)] overflow-y-auto">
              {catalog.map((cat) => (
                <div key={cat.id} className="border-b border-slate-100 last:border-b-0">
                  <button
                    onClick={() => toggleCat(cat.id)}
                    className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-slate-50 transition-colors"
                  >
                    <span className="text-sm font-medium text-slate-700 truncate">
                      {cat.display_name}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {activeFilters.some((f) =>
                        cat.features.some((cf) => cf.feature_key === f.feature_key)
                      ) && (
                        <span className="w-2 h-2 rounded-full bg-indigo-500" />
                      )}
                      <span className="text-[10px] text-slate-400">{cat.features.length}</span>
                      {expandedCats.has(cat.id) ? (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </button>

                  {expandedCats.has(cat.id) && (
                    <div className="px-3 pb-3 space-y-1">
                      {cat.features.map((feat) => {
                        const isActive = activeFilters.some(
                          (f) => f.feature_key === feat.feature_key
                        );
                        return (
                          <button
                            key={feat.id}
                            onClick={() => toggleFilter(feat)}
                            className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors ${
                              isActive
                                ? "bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium"
                                : "text-slate-600 hover:bg-slate-100 border border-transparent"
                            }`}
                          >
                            <span className="flex items-center gap-2">
                              <span
                                className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[9px] ${
                                  isActive
                                    ? "bg-indigo-600 border-indigo-600 text-white"
                                    : "border-slate-300"
                                }`}
                              >
                                {isActive && "✓"}
                              </span>
                              {feat.display_name}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Search button */}
            <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 rounded-b-lg">
              <button
                onClick={runSearch}
                disabled={activeFilters.length === 0 || searching}
                className="w-full py-2 px-4 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {searching ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Szukaj ({activeFilters.length} filtrów)
              </button>
            </div>
          </div>
        </div>

        {/* ── Right: Results ── */}
        <div className="flex-1 min-w-0">
          {/* Active filters bar */}
          {activeFilters.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-1.5">
              {activeFilters.map((f) => (
                <span
                  key={f.feature_key}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"
                >
                  {f.display_name}
                  <button
                    onClick={() =>
                      setActiveFilters((prev) =>
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

          {searching && (
            <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" />
              <span className="text-sm text-slate-500">Przeszukuję bazę pojazdów...</span>
            </div>
          )}

          {hasSearched && !searching && results.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
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

          {hasSearched && !searching && results.length > 0 && (
            <div className="space-y-3">
              <div className="text-xs text-slate-500 mb-2">
                Znaleziono <span className="font-bold text-slate-700">{totalCount}</span> pojazdów
                {totalCount > results.length && (
                  <span> (wyświetlono {results.length})</span>
                )}
              </div>

              {results.map((r) => (
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
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
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
      </div>
    </div>
  );
}
