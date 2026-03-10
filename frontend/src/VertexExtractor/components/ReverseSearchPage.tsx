import { useState, useEffect, useCallback } from "react";
import { Search, Filter, X, Loader2, Car, ChevronDown, ChevronRight } from "lucide-react";

/* ── Types ────────────────────────────────────────────────────── */

interface CatalogFeature {
  id: string;
  feature_key: string;
  display_name: string;
  feature_type: string;
  category_id: string;
  applicable_body_types: string[] | null;
  metadata?: { options?: string[] } | null;
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

const BODY_TYPES = [
  "SUV", "Hatchback", "Kombi", "Sedan", "Furgon",
  "Skrzynia", "Chłodnia", "Kontener", "Izoterma",
  "Platforma", "Wywrotka", "Plandeka", "Brygadówka",
  "Minibus", "KombiVan", "Pick-up", "Coupe", "Kabriolet"
];

interface SearchResult {
  source_vehicle_id: string;
  brand: string | null;
  model: string | null;
  matched_features: number;
  total_filters: number;
  match_score: number;
  price_netto?: number | null;
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
  const [vehicleScope, setVehicleScope] = useState<"all" | "passenger" | "commercial">("all");
  const [bodyTypes, setBodyTypes] = useState<string[]>([]);
  const [bodyTypeSearch, setBodyTypeSearch] = useState("");
  const [showBodyTypeDropdown, setShowBodyTypeDropdown] = useState(false);

  // Price configuration state
  const [priceMin, setPriceMin] = useState<number | "">("");
  const [priceMax, setPriceMax] = useState<number | "">("");
  const [priceMonths, setPriceMonths] = useState<number>(48);
  const [priceMileage, setPriceMileage] = useState<number>(20000);
  const [priceDepositPct, setPriceDepositPct] = useState<number>(0);

  const baseUrl = import.meta.env.VITE_API_URL || "";

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
            value_bool: (feature.feature_type === "boolean" || feature.feature_type === "bool") ? true : undefined,
          },
        ];
      });
    },
    []
  );

  const updateFilter = useCallback((featureKey: string, updates: Partial<SearchFilter>) => {
    setActiveFilters((prev) => prev.map((f) => f.feature_key === featureKey ? { ...f, ...updates } : f));
  }, []);

  // Search
  const runSearch = useCallback(async () => {
    if (activeFilters.length === 0 && bodyTypes.length === 0 && vehicleScope === "all") return;
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
          body_types: bodyTypes.length > 0 ? bodyTypes : undefined,
          vehicle_scope: vehicleScope !== "all" ? vehicleScope : undefined,
          limit: 50,
          offset: 0,
          price_min: priceMin !== "" ? Number(priceMin) : undefined,
          price_max: priceMax !== "" ? Number(priceMax) : undefined,
          price_months: priceMonths,
          price_mileage: priceMileage,
          price_deposit_pct: priceDepositPct,
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
  }, [activeFilters, bodyTypes, vehicleScope, baseUrl, priceMin, priceMax, priceMonths, priceMileage, priceDepositPct]);

  const clearFilters = () => {
    setActiveFilters([]);
    setBodyTypes([]);
    setVehicleScope("all");
    setPriceMin("");
    setPriceMax("");
    setPriceMonths(48);
    setPriceMileage(20000);
    setPriceDepositPct(0);
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
            {/* Scope Filter */}
            <div className="p-4 border-b border-slate-200 rounded-t-lg bg-slate-50">
               <label className="text-xs font-semibold text-slate-800 uppercase tracking-wider block mb-3">Segment Pojazdu</label>
               <div className="flex bg-slate-200/50 p-1 rounded-md">
                 <button
                   onClick={() => setVehicleScope("all")}
                   className={`flex-1 text-xs py-1.5 rounded-sm font-medium transition-colors ${vehicleScope === "all" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
                 >
                   Wszystkie
                 </button>
                 <button
                   onClick={() => setVehicleScope("passenger")}
                   className={`flex-1 text-xs py-1.5 rounded-sm font-medium transition-colors ${vehicleScope === "passenger" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
                 >
                   Osobowe
                 </button>
                 <button
                   onClick={() => setVehicleScope("commercial")}
                   className={`flex-1 text-xs py-1.5 rounded-sm font-medium transition-colors ${vehicleScope === "commercial" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
                 >
                   Dostawcze
                 </button>
               </div>
            </div>

            {/* Body Type Filter */}
            <div className="p-4 border-b border-slate-200 relative">
               <label className="text-xs font-semibold text-slate-800 uppercase tracking-wider block mb-2">Typ Zabudowy</label>
               <div className="relative">
                 <button
                   onClick={() => setShowBodyTypeDropdown(!showBodyTypeDropdown)}
                   className="w-full text-left text-sm border border-slate-200 rounded-md px-3 py-2 bg-white flex items-center justify-between hover:border-indigo-300 transition-colors"
                 >
                   <span className="truncate text-slate-700 font-medium">
                     {bodyTypes.length === 0 ? "Wybierz typy..." : `Wybrano (${bodyTypes.length})`}
                   </span>
                   <ChevronDown className="w-4 h-4 text-slate-400" />
                 </button>

                 {showBodyTypeDropdown && (
                   <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-md shadow-lg p-2">
                     <div className="relative mb-2">
                       <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                       <input
                         type="text"
                         placeholder="Szukaj zabudowy..."
                         value={bodyTypeSearch}
                         onChange={(e) => setBodyTypeSearch(e.target.value)}
                         className="w-full pl-7 pr-2 py-1.5 text-xs border border-slate-200 rounded focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                         onClick={(e) => e.stopPropagation()}
                       />
                     </div>
                     <div className="max-h-48 overflow-y-auto space-y-0.5">
                       {BODY_TYPES.filter(bt => bt.toLowerCase().includes(bodyTypeSearch.toLowerCase())).map(bt => (
                         <label key={bt} className="flex items-center gap-2 px-2 py-1.5 hover:bg-slate-50 rounded cursor-pointer">
                           <input
                             type="checkbox"
                             checked={bodyTypes.includes(bt)}
                             onChange={(e) => {
                               if (e.target.checked) setBodyTypes([...bodyTypes, bt]);
                               else setBodyTypes(bodyTypes.filter(t => t !== bt));
                             }}
                             className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                           />
                           <span className="text-xs text-slate-700">{bt}</span>
                         </label>
                       ))}
                       {BODY_TYPES.filter(bt => bt.toLowerCase().includes(bodyTypeSearch.toLowerCase())).length === 0 && (
                         <div className="text-xs text-slate-400 text-center py-2">Brak wyników</div>
                       )}
                     </div>
                   </div>
                 )}
               </div>
               
               {bodyTypes.length > 0 && (
                 <div className="flex flex-wrap gap-1 mt-2">
                   {bodyTypes.map(bt => (
                     <span key={bt} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                       {bt}
                       <button onClick={() => setBodyTypes(bodyTypes.filter(t => t !== bt))} className="hover:text-red-500">
                         <X className="w-2.5 h-2.5" />
                       </button>
                     </span>
                   ))}
                 </div>
               )}
            </div>

             {/* Price & Budget Filter */}
             <div className="p-4 border-b border-slate-200 bg-slate-50/50">
               <label className="text-xs font-semibold text-slate-800 uppercase tracking-wider block mb-3">Budżet i Parametry LTR</label>
               
               <div className="space-y-3">
                 <div className="flex gap-2 items-center">
                   <div className="flex-1">
                     <span className="text-[10px] text-slate-500 font-medium mb-1 block">Rata Od (PLN netto)</span>
                     <input
                       type="number"
                       value={priceMin}
                       onChange={(e) => setPriceMin(e.target.value === "" ? "" : Number(e.target.value))}
                       placeholder="Min rata"
                       className="w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:ring-1 focus:border-indigo-500 outline-none"
                     />
                   </div>
                   <div className="flex-1">
                     <span className="text-[10px] text-slate-500 font-medium mb-1 block">Rata Do (PLN netto)</span>
                     <input
                       type="number"
                       value={priceMax}
                       onChange={(e) => setPriceMax(e.target.value === "" ? "" : Number(e.target.value))}
                       placeholder="Max rata"
                       className="w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:ring-1 focus:border-indigo-500 outline-none"
                     />
                   </div>
                 </div>

                 <div className="flex gap-2 items-center">
                   <div className="flex-1">
                     <span className="text-[10px] text-slate-500 font-medium mb-1 block">Okres (mc)</span>
                     <select
                       value={priceMonths}
                       onChange={(e) => setPriceMonths(Number(e.target.value))}
                       className="w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:ring-1 focus:border-indigo-500 outline-none bg-white"
                     >
                       <option value={24}>24</option>
                       <option value={36}>36</option>
                       <option value={48}>48</option>
                       <option value={60}>60</option>
                     </select>
                   </div>
                   <div className="flex-1">
                     <span className="text-[10px] text-slate-500 font-medium mb-1 block">Przebieg roczny</span>
                     <select
                       value={priceMileage}
                       onChange={(e) => setPriceMileage(Number(e.target.value))}
                       className="w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:ring-1 focus:border-indigo-500 outline-none bg-white"
                     >
                       <option value={10000}>10.000 km</option>
                       <option value={20000}>20.000 km</option>
                       <option value={30000}>30.000 km</option>
                       <option value={40000}>40.000 km</option>
                       <option value={50000}>50.000 km</option>
                       <option value={60000}>60.000 km</option>
                     </select>
                   </div>
                 </div>

                 <div>
                   <span className="text-[10px] text-slate-500 font-medium mb-1 block">Wkład Własny (%)</span>
                   <select
                     value={priceDepositPct}
                     onChange={(e) => setPriceDepositPct(Number(e.target.value))}
                     className="w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:ring-1 focus:border-indigo-500 outline-none bg-white"
                   >
                     <option value={0}>0%</option>
                     <option value={5}>5%</option>
                     <option value={10}>10%</option>
                     <option value={15}>15%</option>
                     <option value={20}>20%</option>
                   </select>
                 </div>
                 
               </div>
             </div>

            {/* Filter header */}
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5" />
                Dostępne Cechy
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
                      {cat.features
                        .filter(f => bodyTypes.length === 0 || !f.applicable_body_types?.length || bodyTypes.some(bt => f.applicable_body_types!.includes(bt)))
                        .map((feat) => {
                        const activeFlt = activeFilters.find((f) => f.feature_key === feat.feature_key);
                        const isActive = !!activeFlt;
                        return (
                          <div key={feat.id} className="mb-0.5">
                            <button
                              onClick={() => toggleFilter(feat)}
                              className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors ${
                                isActive
                                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium"
                                  : "text-slate-600 hover:bg-slate-100 border border-transparent"
                              }`}
                            >
                              <span className="flex items-center gap-2">
                                <span
                                  className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[9px] shrink-0 ${
                                    isActive
                                      ? "bg-indigo-600 border-indigo-600 text-white"
                                      : "border-slate-300"
                                  }`}
                                >
                                  {isActive && "✓"}
                                </span>
                                <span className={!isActive ? "truncate" : ""}>{feat.display_name}</span>
                              </span>
                            </button>
                            {/* Dynamic Inputs For Selected Filters */}
                            {isActive && feat.feature_type === "numeric" && (
                              <div className="pl-8 pr-3 pb-2 flex items-center gap-2 mt-1">
                                <input type="number" placeholder="Min" className="w-16 h-7 px-1.5 border border-indigo-200 rounded text-xs outline-none focus:border-indigo-400 bg-white" value={activeFlt.value_num_min || ""} onChange={(e) => updateFilter(feat.feature_key, { value_num_min: e.target.value ? Number(e.target.value) : undefined })} />
                                <span className="text-indigo-300 text-[10px]">-</span>
                                <input type="number" placeholder="Max" className="w-16 h-7 px-1.5 border border-indigo-200 rounded text-xs outline-none focus:border-indigo-400 bg-white" value={activeFlt.value_num_max || ""} onChange={(e) => updateFilter(feat.feature_key, { value_num_max: e.target.value ? Number(e.target.value) : undefined })} />
                              </div>
                            )}
                            {isActive && feat.feature_type === "enum" && feat.metadata?.options && (
                              <div className="pl-8 pr-3 pb-2 mt-1">
                                <select 
                                  className="w-full h-7 px-2 border border-indigo-200 rounded text-xs outline-none focus:border-indigo-400 bg-white text-slate-700" 
                                  value={activeFlt.value_text || ""} 
                                  onChange={(e) => updateFilter(feat.feature_key, { value_text: e.target.value || undefined })}
                                >
                                  <option value="">-- wybierz --</option>
                                  {feat.metadata.options.map(opt => (
                                    <option key={opt} value={opt}>{opt}</option>
                                  ))}
                                </select>
                              </div>
                            )}
                            {isActive && (feat.feature_type === "text" || (feat.feature_type === "enum" && !feat.metadata?.options)) && (
                              <div className="pl-8 pr-3 pb-2 mt-1">
                                <input type="text" placeholder="Szukana wartość..." className="w-full h-7 px-2 border border-indigo-200 rounded text-xs outline-none focus:border-indigo-400 bg-white" value={activeFlt.value_text || ""} onChange={(e) => updateFilter(feat.feature_key, { value_text: e.target.value || undefined })} />
                              </div>
                            )}
                          </div>
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
                disabled={(activeFilters.length === 0 && bodyTypes.length === 0 && vehicleScope === "all") || searching}
                className="w-full py-2 px-4 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {searching ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Szukaj ({activeFilters.length + bodyTypes.length + (vehicleScope !== "all" ? 1 : 0)} filtrów)
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
                    
                    {r.price_netto !== undefined && r.price_netto !== null && (
                      <div className="ml-2 pl-3 py-1 border-l border-slate-200 text-right">
                        <div className="text-sm font-bold text-slate-800">
                          {r.price_netto.toFixed(0)} <span className="text-[10px] font-normal text-slate-500">PLN/mc</span>
                        </div>
                        <div className="text-[9px] text-slate-400 uppercase tracking-tight">Cena Netto</div>
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
      </div>
    </div>
  );
}
