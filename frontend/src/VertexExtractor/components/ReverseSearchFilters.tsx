import { useCallback } from "react";
import { Search, ChevronDown, ChevronRight, Settings2, Loader2 } from "lucide-react";
import { CatalogFeature, SearchFilter, getSliderBounds, CURATED_SHARED, CURATED_PASSENGER, CURATED_COMMERCIAL } from "../types";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function ReverseSearchFilters({ state, actions }: { state: any; actions: any }) {
  const {
    catalog, activeFilters, expandedCats, facets, vehicleScope, bodyTypes, bodyTypeSearch,
    showBodyTypeDropdown, showAdvancedFilters, dbBodyTypes, priceMin, priceMax, priceMonths,
    priceMileage, priceDepositPct, priceMarginPct, globalSearchQuery, searching
  } = state;
  const {
    setExpandedCats, setFeatureFilter, setVehicleScope, setShowBodyTypeDropdown, setBodyTypeSearch,
    setBodyTypes, setPriceMin, setPriceMax, setPriceMonths, setPriceMileage, setPriceDepositPct, setPriceMarginPct,
    setShowAdvancedFilters, runSearch, clearFilters
  } = actions;

  const toggleCat = (catId: string) => {
    setExpandedCats((prev: Set<string>) => {
      const next = new Set(prev);
      if (next.has(catId)) next.delete(catId);
      else next.add(catId);
      return next;
    });
  };

  const matchCuratedFeatures = useCallback((preferredKeys: string[]) => {
    const matched: CatalogFeature[] = [];
    const usedIds = new Set<string>();

    for (const key of preferredKeys) {
      for (const cat of catalog) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const found = cat.features.find((f: any) => 
          f.feature_key === key || 
          f.feature_key.includes(key) || 
          f.display_name.toLowerCase().includes(key.replace(/_/g, " "))
        );
        if (found && !usedIds.has(found.id)) {
          matched.push(found);
          usedIds.add(found.id);
          break;
        }
      }
    }
    return matched;
  }, [catalog]);

  const renderFeature = useCallback((feat: CatalogFeature) => {
    const activeFlt = activeFilters.find((f: SearchFilter) => f.feature_key === feat.feature_key);
    const isActive = !!activeFlt;

    return (
      <div key={feat.id} className="mb-0.5">
        {(feat.feature_type === "boolean" || feat.feature_type === "bool") ? (
          <label className={`flex items-start gap-2 px-3 py-2 rounded text-xs cursor-pointer transition-colors border ${isActive ? "bg-indigo-50 border-indigo-200" : "bg-white border-slate-100 hover:bg-slate-50"}`}>
            <input 
              type="checkbox" 
              className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600 w-3.5 h-3.5 shrink-0"
              checked={!!activeFlt?.value_bool}
              onChange={(e) => setFeatureFilter(feat, "value_bool", e.target.checked ? true : undefined)}
            />
            <span className={`font-medium flex-1 pt-0.5 ${isActive ? "text-indigo-700" : "text-slate-700"}`}>{feat.display_name}</span>
            {(!isActive && Object.keys(facets).length > 0 && facets[feat.feature_key] !== undefined) && (
              <span className="text-[10px] shrink-0 text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded-full font-medium self-start mt-0.5 border border-slate-200" title={`Dostępne w ${facets[feat.feature_key]} autach z obecnego wyniku`}>
                {facets[feat.feature_key]}
              </span>
            )}
          </label>
        ) : feat.feature_type === "numeric" ? (
          <div className={`px-3 py-2 border rounded transition-colors ${isActive ? "bg-indigo-50 border-indigo-200" : "bg-white border-slate-100 hover:bg-slate-50"}`}>
              <div className={`text-xs font-medium mb-1.5 flex items-center justify-between ${isActive ? "text-indigo-700" : "text-slate-700"}`}>
                <span>{feat.display_name}</span>
                {isActive && (activeFlt?.value_num_min || activeFlt?.value_num_max) && (
                  <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                    {activeFlt?.value_num_min ?? '0'} - {activeFlt?.value_num_max ?? 'Max'}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mb-2">
                <input 
                  type="number" 
                  placeholder="Min" 
                  className="w-full h-7 px-2 border border-slate-200 rounded text-xs outline-none focus:border-indigo-400 bg-white" 
                  value={activeFlt?.value_num_min ?? ""} 
                  onChange={(e) => setFeatureFilter(feat, "value_num_min", e.target.value !== "" ? Number(e.target.value) : undefined)} 
                />
                <span className="text-slate-400 text-xs">-</span>
                <input 
                  type="number" 
                  placeholder="Max" 
                  className="w-full h-7 px-2 border border-slate-200 rounded text-xs outline-none focus:border-indigo-400 bg-white" 
                  value={activeFlt?.value_num_max ?? ""} 
                  onChange={(e) => setFeatureFilter(feat, "value_num_max", e.target.value !== "" ? Number(e.target.value) : undefined)} 
                />
              </div>
              <div className="flex flex-col gap-1.5 mt-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 w-6">Min</span>
                  <input 
                    type="range"
                    min={getSliderBounds(feat.display_name).min}
                    max={getSliderBounds(feat.display_name).max}
                    className="w-full accent-indigo-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    value={activeFlt?.value_num_min ?? getSliderBounds(feat.display_name).min}
                    onChange={(e) => setFeatureFilter(feat, "value_num_min", Number(e.target.value))}
                    title="Min"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 w-6">Max</span>
                  <input 
                    type="range"
                    min={getSliderBounds(feat.display_name).min}
                    max={getSliderBounds(feat.display_name).max}
                    className="w-full accent-indigo-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    value={activeFlt?.value_num_max ?? getSliderBounds(feat.display_name).max}
                    onChange={(e) => setFeatureFilter(feat, "value_num_max", Number(e.target.value))}
                    title="Max"
                  />
                </div>
              </div>
          </div>
        ) : feat.feature_type === "enum" && feat.metadata?.options ? (
          <div className={`px-3 py-2 border rounded transition-colors ${isActive ? "bg-indigo-50 border-indigo-200" : "bg-white border-slate-100 hover:bg-slate-50"}`}>
            <div className={`text-xs font-medium mb-1.5 ${isActive ? "text-indigo-700" : "text-slate-700"}`}>{feat.display_name}</div>
            <select 
              className="w-full h-7 px-2 border border-slate-200 rounded text-xs outline-none focus:border-indigo-400 bg-white text-slate-700" 
              value={activeFlt?.value_text || ""} 
              onChange={(e) => setFeatureFilter(feat, "value_text", e.target.value || undefined)}
            >
              <option value="">-- dowolna --</option>
              {feat.metadata.options.map((opt: string) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
        ) : (
          <div className={`px-3 py-2 border rounded transition-colors ${isActive ? "bg-indigo-50 border-indigo-200" : "bg-white border-slate-100 hover:bg-slate-50"}`}>
            <div className={`text-xs font-medium mb-1.5 flex items-center justify-between ${isActive ? "text-indigo-700" : "text-slate-700"}`}>
              <span>{feat.display_name}</span>
              {isActive && activeFlt?.value_text && (
                  <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                    {activeFlt?.value_text}
                  </span>
              )}
            </div>
            <input 
              type="text" 
              placeholder="Wpisz wartość..." 
              className="w-full h-7 px-2 border border-slate-200 rounded text-xs outline-none focus:border-indigo-400 bg-white mb-2" 
              value={activeFlt?.value_text || ""} 
              onChange={(e) => setFeatureFilter(feat, "value_text", e.target.value || undefined)} 
            />
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] text-slate-400 w-6">Wart.</span>
              <input 
                type="range"
                min={getSliderBounds(feat.display_name).min}
                max={getSliderBounds(feat.display_name).max}
                className="w-full accent-indigo-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                value={Number(activeFlt?.value_text) || getSliderBounds(feat.display_name).min}
                onChange={(e) => setFeatureFilter(feat, "value_text", e.target.value)}
                title="Wartość"
              />
            </div>
          </div>
        )}
      </div>
    );
  }, [activeFilters, setFeatureFilter, facets]);

  const curatedSharedFeatures = matchCuratedFeatures(CURATED_SHARED);
  const curatedPassengerFeatures = matchCuratedFeatures(CURATED_PASSENGER);
  const curatedCommercialFeatures = matchCuratedFeatures(CURATED_COMMERCIAL);

  const curatedFeaturesToRender = vehicleScope === "commercial" 
      ? [...curatedSharedFeatures, ...curatedCommercialFeatures]
      : [...curatedSharedFeatures, ...curatedPassengerFeatures];

  return (
    <div className="w-80 shrink-0">
      <div className="bg-white border border-slate-200 rounded-lg shadow-sm sticky top-4 max-h-[calc(100vh-2rem)] flex flex-col">
        {/* Scrollable Filters Content */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {/* Scope Filter */}
          <div className="p-4 border-b border-slate-200 rounded-t-lg bg-slate-50">
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-semibold text-slate-800 uppercase tracking-wider block">Segment Pojazdu</label>
              {(activeFilters.length > 0 || bodyTypes.length > 0 || vehicleScope !== "all" || priceMin !== "" || priceMax !== "") && (
                <button
                  onClick={clearFilters}
                  className="text-[10px] text-slate-500 hover:text-red-600 uppercase font-bold"
                >
                  Wyczyść filtry
                </button>
              )}
            </div>
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
                    {dbBodyTypes.filter((bt: string) => bt.toLowerCase().includes(bodyTypeSearch.toLowerCase())).map((bt: string) => (
                      <label key={bt} className="flex items-center gap-2 px-2 py-1.5 hover:bg-slate-50 rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={bodyTypes.includes(bt)}
                          onChange={(e) => {
                            if (e.target.checked) setBodyTypes([...bodyTypes, bt]);
                            else setBodyTypes(bodyTypes.filter((t: string) => t !== bt));
                          }}
                          className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                        />
                        <span className="text-xs text-slate-700">{bt}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Pricing Config */}
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <label className="text-xs font-semibold text-slate-800 uppercase tracking-wider block mb-3">Zakres Raty Netto / mc</label>
            <div className="flex items-center gap-2 mb-3">
              <input 
                type="number" 
                placeholder="Od PLN" 
                className="w-full h-8 px-2 border border-slate-200 rounded-md text-sm outline-none focus:border-indigo-400" 
                value={priceMin} 
                onChange={(e) => setPriceMin(e.target.value)} 
              />
              <span className="text-slate-400">-</span>
              <input 
                type="number" 
                placeholder="Do PLN" 
                className="w-full h-8 px-2 border border-slate-200 rounded-md text-sm outline-none focus:border-indigo-400" 
                value={priceMax} 
                onChange={(e) => setPriceMax(e.target.value)} 
              />
            </div>

            <div className="space-y-3 pt-3 border-t border-slate-200">
              <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Do kalkulacji wyników:</label>
              
              <div className="grid grid-cols-2 gap-3">
                {/* 1) Months */}
                <div>
                  <div className="flex items-center justify-between mb-1 text-[10px] text-slate-600">
                    <span>Okres</span>
                    <span className="font-bold">{priceMonths} m-cy</span>
                  </div>
                  <input
                    type="range"
                    min="12"
                    max="84"
                    step="12"
                    value={priceMonths}
                    onChange={(e) => setPriceMonths(Number(e.target.value))}
                    className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                {/* 2) Mileage */}
                <div>
                  <div className="flex items-center justify-between mb-1 text-[10px] text-slate-600">
                    <span>Przebieg</span>
                    <span className="font-bold">{priceMileage / 1000}k /rok</span>
                  </div>
                  <input
                    type="range"
                    min="10000"
                    max="60000"
                    step="5000"
                    value={priceMileage}
                    onChange={(e) => setPriceMileage(Number(e.target.value))}
                    className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>
              </div>

              {/* 3) Deposit */}
              <div>
                <div className="flex items-center justify-between mb-1 text-[10px] text-slate-600">
                  <span>Wpłata (+ dotacja)</span>
                  <span className="font-bold">{priceDepositPct}% wartości</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="45"
                  step="5"
                  value={priceDepositPct}
                  onChange={(e) => setPriceDepositPct(Number(e.target.value))}
                  className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              {/* 4) Margin */}
              <div>
                <div className="flex items-center justify-between mb-1 text-[10px] text-slate-600">
                  <span className={priceMarginPct === "" ? "text-red-500 font-bold" : ""}>Marża sprzedaży</span>
                  <span className={`font-bold ${priceMarginPct === "" ? "text-red-500 uppercase" : ""}`}>{priceMarginPct === "" ? "Wymagana" : `${priceMarginPct}%`}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="20"
                  step="0.5"
                  value={priceMarginPct === "" ? 0 : priceMarginPct}
                  onChange={(e) => setPriceMarginPct(Number(e.target.value))}
                  className={`w-full h-1 rounded-lg appearance-none cursor-pointer ${priceMarginPct === "" ? "bg-red-200 accent-red-500" : "bg-slate-200 accent-indigo-500"}`}
                />
                {priceMarginPct === "" && (
                  <p className="text-[9px] text-red-500 mt-1 leading-tight">Ustaw marżę, aby odblokować wyceny LTR.</p>
                )}
              </div>
            </div>
          </div>

          <div className="p-2 space-y-1 bg-slate-50 pb-4">
            {/* Quick Filters (Curated) */}
            {!showAdvancedFilters && curatedFeaturesToRender.length > 0 && (
              <div className="px-2 pt-2">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-2 px-1">Szybkie Filtry (Najbliższe dla typu)</label>
                <div className="space-y-1">
                  {curatedFeaturesToRender.map(renderFeature)}
                </div>
              </div>
            )}

            {/* Advanced Filters (All Categories) */}
            {showAdvancedFilters && catalog.map((cat: CatalogCategory) => {
              // Filtracja cech w pojeździe – to samo
              const matchingFeatures = cat.features;
              if (matchingFeatures.length === 0) return null;

              const isExpanded = expandedCats.has(cat.id);
              const activeCount = matchingFeatures.filter((f: CatalogFeature) => activeFilters.some((af: SearchFilter) => af.feature_key === f.feature_key)).length;

              return (
                <div key={cat.id} className="bg-white border border-slate-100 rounded shadow-sm overflow-hidden">
                  <button
                    onClick={() => toggleCat(cat.id)}
                    className="w-full px-3 py-2.5 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors"
                  >
                    <span className="text-xs font-semibold text-slate-700">{cat.display_name}</span>
                    <div className="flex items-center gap-2">
                      {activeCount > 0 && (
                        <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-[10px] font-bold flex items-center justify-center">
                          {activeCount}
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-3 pb-3 space-y-1">
                      {matchingFeatures
                        .filter((f: CatalogFeature) => bodyTypes.length === 0 || !f.applicable_body_types?.length || bodyTypes.some((bt: string) => f.applicable_body_types!.includes(bt)))
                        .map(renderFeature)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Advanced Filters Toggle */}
        <div className="px-4 py-2 border-t border-slate-200 bg-white flex justify-center shrink-0">
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="text-xs text-slate-500 hover:text-indigo-600 font-medium flex items-center gap-1.5 transition-colors"
            >
              <Settings2 className="w-3.5 h-3.5" />
              {showAdvancedFilters ? "Wróć do głównych filtrów" : "Pokaż wszystkie filtry"}
            </button>
        </div>

        {/* Search button */}
        <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 rounded-b-lg shrink-0">
          <button
            onClick={runSearch}
            disabled={(globalSearchQuery.trim() === "" && activeFilters.length === 0 && bodyTypes.length === 0 && vehicleScope === "all") || searching}
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
  );
}
