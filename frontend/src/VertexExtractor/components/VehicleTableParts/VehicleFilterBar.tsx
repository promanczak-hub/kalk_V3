import { useCallback, useRef, useEffect, useState } from "react";
import {
  ArrowUpDown,
  Search,
  Calendar,
  Trash2,
  GitCompareArrows,
  X,
  Check,
  RotateCcw,
  ChevronDown,
  Filter,
  Activity
} from "lucide-react";
import { format } from "date-fns";
import type { SortKey, SortDir } from "../../hooks/useVehicleFilters";
import { formatPrice } from "./PriceDualFormat";

interface VehicleFilterBarProps {
  // Sort
  sortKey: SortKey;
  sortDir: SortDir;
  onSortKeyChange: (key: SortKey) => void;
  // Live search
  liveSearchText: string;
  onLiveSearchChange: (text: string) => void;
  
  // Date range
  dateRange: [number, number];
  dateBounds: { dateMin: number; dateMax: number };
  onDateRangeChange: (range: [number, number]) => void;

  // Price range
  priceRange: [number, number];
  priceBounds: { priceMin: number; priceMax: number };
  onPriceRangeChange: (range: [number, number]) => void;

  // Multi-select dropdowns
  availableBrands: string[];
  selectedBrands: string[];
  onSelectedBrandsChange: (brands: string[]) => void;

  availableFuels: string[];
  selectedFuels: string[];
  onSelectedFuelsChange: (fuels: string[]) => void;

  availableSamarClasses: string[];
  selectedSamarClasses: string[];
  onSelectedSamarClassesChange: (classes: string[]) => void;

  availableBodyTypes: string[];
  selectedBodyTypes: string[];
  onSelectedBodyTypesChange: (types: string[]) => void;

  availableTransmissions: string[];
  selectedTransmissions: string[];
  onSelectedTransmissionsChange: (transmissions: string[]) => void;

  availableDrives: string[];
  selectedDrives: string[];
  onSelectedDrivesChange: (drives: string[]) => void;

  powerRange: [number, number];
  powerBounds: { powerMin: number; powerMax: number };
  onPowerRangeChange: (range: [number, number]) => void;

  kosztDziennyRange: [number, number];
  kosztDziennyBounds: { kosztDziennyMin: number; kosztDziennyMax: number };
  onKosztDziennyRangeChange: (range: [number, number]) => void;

  // Reset
  onResetFilters: () => void;
  
  // Selection
  selectedCount: number;
  totalVisible: number;
  allVisibleSelected: boolean;
  onToggleSelectAll: () => void;
  onDeleteSelected: () => void;
  onCompareSelected: () => void;
}

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "created_at", label: "Data" },
  { key: "brand", label: "Marka" },
  { key: "model", label: "Model" },
  { key: "samar_category", label: "Klasa SAMAR" },
  { key: "fuel", label: "Paliwo" },
  { key: "price", label: "Cena" },
];

function MultiSelectDropdown({
  label,
  options,
  selectedOptions,
  onChange,
}: {
  label: string;
  options: string[];
  selectedOptions: string[];
  onChange: (selected: string[]) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const safeOptions = options || [];
  const safeSelectedOptions = selectedOptions || [];

  const filteredOptions = safeOptions.filter((o) =>
    o.toLowerCase().includes(search.toLowerCase())
  );

  const toggleOption = (option: string) => {
    if (safeSelectedOptions.includes(option)) {
      onChange(safeSelectedOptions.filter((o) => o !== option));
    } else {
      onChange([...safeSelectedOptions, option]);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border transition-all ${
          safeSelectedOptions.length > 0
            ? "border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100"
            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
        }`}
      >
        <Filter className="w-3.5 h-3.5" />
        {label}
        {safeSelectedOptions.length > 0 && (
          <span className="ml-1 px-1.5 py-0.5 rounded-full bg-blue-200 text-blue-800 text-[10px] tabular-nums">
            {safeSelectedOptions.length}
          </span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 ml-1 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 max-w-xs w-64 bg-white border border-slate-200 rounded-lg shadow-xl z-50 overflow-hidden flex flex-col">
          <div className="p-2 border-b border-slate-100 bg-slate-50">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Szukaj..."
                className="w-full pl-7 pr-3 py-1.5 text-xs border border-slate-200 rounded-md outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="max-h-60 overflow-y-auto p-1">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-500">Brak wyników</div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = safeSelectedOptions.includes(opt);
                return (
                  <label
                    key={opt}
                    className="flex items-center gap-2.5 px-3 py-2 hover:bg-slate-50 cursor-pointer rounded-md transition-colors"
                  >
                    <div
                      className={`flex-shrink-0 w-4 h-4 border rounded flex items-center justify-center transition-colors ${
                        isSelected ? "bg-blue-500 border-blue-500" : "bg-white border-slate-300"
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <span className={`text-xs truncate ${isSelected ? "font-medium text-slate-900" : "text-slate-700"}`}>
                      {opt}
                    </span>
                    <input type="checkbox" className="hidden" checked={isSelected} onChange={() => toggleOption(opt)} />
                  </label>
                );
              })
            )}
          </div>
          {safeSelectedOptions.length > 0 && (
            <div className="p-2 border-t border-slate-100 bg-slate-50">
              <button
                type="button"
                onClick={() => onChange([])}
                className="w-full py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-md hover:bg-slate-100 transition-colors"
              >
                Wyczyść ({safeSelectedOptions.length})
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function VehicleFilterBar({
  sortKey,
  sortDir,
  onSortKeyChange,
  liveSearchText,
  onLiveSearchChange,
  dateRange,
  dateBounds,
  onDateRangeChange,
  priceRange,
  priceBounds,
  onPriceRangeChange,
  availableBrands,
  selectedBrands,
  onSelectedBrandsChange,
  availableFuels,
  selectedFuels,
  onSelectedFuelsChange,
  availableSamarClasses,
  selectedSamarClasses,
  onSelectedSamarClassesChange,
  availableBodyTypes,
  selectedBodyTypes,
  onSelectedBodyTypesChange,
  availableTransmissions,
  selectedTransmissions,
  onSelectedTransmissionsChange,
  availableDrives,
  selectedDrives,
  onSelectedDrivesChange,
  powerRange,
  powerBounds,
  onPowerRangeChange,
  kosztDziennyRange,
  kosztDziennyBounds,
  onKosztDziennyRangeChange,
  onResetFilters,
  selectedCount,
  totalVisible,
  allVisibleSelected,
  onToggleSelectAll,
  onDeleteSelected,
  onCompareSelected,
}: VehicleFilterBarProps) {
  const [localSearch, setLocalSearch] = useState(liveSearchText);
  const [isRangeExpanded, setIsRangeExpanded] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchInput = useCallback(
    (value: string) => {
      setLocalSearch(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => onLiveSearchChange(value), 300);
    },
    [onLiveSearchChange],
  );

  useEffect(() => {
    setLocalSearch(liveSearchText);
  }, [liveSearchText]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const hasActiveFilters =
    liveSearchText.length > 0 ||

    selectedBrands.length > 0 ||
    selectedFuels.length > 0 ||
    selectedSamarClasses.length > 0 ||
    selectedBodyTypes.length > 0 ||
    selectedTransmissions.length > 0 ||
    selectedDrives.length > 0 ||
    dateRange[0] > 0 ||
    dateRange[1] < Infinity ||
    priceRange[0] > 0 ||
    priceRange[1] < Infinity ||
    powerRange[0] > 0 ||
    powerRange[1] < Infinity ||
    kosztDziennyRange[0] > 0 ||
    kosztDziennyRange[1] < Infinity;

  const dateSpan = dateBounds.dateMax - dateBounds.dateMin;
  const priceSpan = priceBounds.priceMax - priceBounds.priceMin;
  const powerSpan = powerBounds.powerMax - powerBounds.powerMin;

  return (
    <div className="space-y-4 mb-5">
      {/* Row 1: Search, Sort, Unmapped flag, Reset */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Search & Sort */}
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[300px]">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={localSearch}
              onChange={(e) => handleSearchInput(e.target.value)}
              placeholder="Skan wyposażenia: klima, tapicerka, xenon..."
              className="w-full pl-9 pr-8 py-2 border border-slate-200 bg-white rounded-lg text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all shadow-sm"
            />
            {localSearch && (
              <button
                onClick={() => handleSearchInput("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-500"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-lg shadow-sm pl-2">
			      <label className="text-xs uppercase font-semibold text-slate-500 tracking-wider whitespace-nowrap">
				      Sortuj:
            </label>
            <select
              value={sortKey}
              onChange={(e) => onSortKeyChange(e.target.value as SortKey)}
              className="text-xs text-slate-700 bg-transparent pl-3 pr-1 py-2 outline-none cursor-pointer font-medium"
            >
              <option value="" disabled>Sortuj po...</option>
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
            <button
              onClick={() => onSortKeyChange(sortKey)}
              className="px-2 py-2 text-slate-400 hover:text-slate-700 border-l border-slate-100 transition-colors"
              title={sortDir === "asc" ? "Rosnąco" : "Malejąco"}
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Unmapped, Reset */}
        <div className="flex items-center gap-3">


          {hasActiveFilters && (
            <button
              onClick={onResetFilters}
              className="flex items-center gap-1.5 px-3 py-2 text-xs uppercase font-bold text-slate-500 hover:text-blue-600 bg-white hover:bg-blue-50 border border-slate-200 rounded-lg shadow-sm transition-colors whitespace-nowrap"
              title="Resetuj wszystkie filtry"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Row 2: Advanced Dropdowns */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
        <span className="text-xs font-semibold uppercase text-slate-500 mr-2 tracking-wider">Filtry Zaawansowane</span>

        <MultiSelectDropdown
          label="Marka"
          options={availableBrands}
          selectedOptions={selectedBrands}
          onChange={onSelectedBrandsChange}
        />

        <MultiSelectDropdown
          label="Silnik / Paliwo"
          options={availableFuels}
          selectedOptions={selectedFuels}
          onChange={onSelectedFuelsChange}
        />

        <MultiSelectDropdown
          label="Klasa SAMAR"
          options={availableSamarClasses}
          selectedOptions={selectedSamarClasses}
          onChange={onSelectedSamarClassesChange}
        />

        <MultiSelectDropdown
          label="Nadwozie"
          options={availableBodyTypes}
          selectedOptions={selectedBodyTypes}
          onChange={onSelectedBodyTypesChange}
        />

        <MultiSelectDropdown
          label="Skrzynia biegów"
          options={availableTransmissions}
          selectedOptions={selectedTransmissions}
          onChange={onSelectedTransmissionsChange}
        />

        <MultiSelectDropdown
          label="Napęd"
          options={availableDrives}
          selectedOptions={selectedDrives}
          onChange={onSelectedDrivesChange}
        />

        <button
          type="button"
          onClick={() => setIsRangeExpanded(prev => !prev)}
          className="ml-auto flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-slate-500 hover:text-slate-700 bg-white border border-slate-200 hover:border-slate-300 rounded-lg transition-colors whitespace-nowrap"
          title={isRangeExpanded ? "Zwiń filtry zakresu" : "Rozwiń filtry zakresu"}
        >
          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isRangeExpanded ? "" : "rotate-180"}`} />
          Zakres
        </button>
      </div>

      {/* Row 3: Sliders (Date, Price, Power, Koszt Dzienny) */}
      {isRangeExpanded && <div className="grid grid-cols-1 md:grid-cols-4 gap-6 bg-slate-50/50 border border-slate-100 rounded-lg px-5 py-4 shadow-inner">
        {/* Date range slider */}
        <div className="flex-1">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" /> Data oferty
            </span>
            <span className="text-xs text-slate-700 tabular-nums font-bold">
              {format(new Date(dateRange[0] > 0 ? dateRange[0] : dateBounds.dateMin), "dd.MM.yyyy")}
              {" — "}
              {format(new Date(dateRange[1] < Infinity ? dateRange[1] : dateBounds.dateMax), "dd.MM.yyyy")}
            </span>
          </div>
          {dateSpan > 0 ? (
            <div className="relative h-6 flex items-center mt-1">
              <input
                type="range"
                min={dateBounds.dateMin}
                max={dateBounds.dateMax}
                step={86400000} // 1 day ms
                value={dateRange[0] > 0 ? dateRange[0] : dateBounds.dateMin}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const maxVal = dateRange[1] < Infinity ? dateRange[1] : dateBounds.dateMax;
                  onDateRangeChange([Math.min(val, maxVal), dateRange[1]]);
                }}
                className="absolute w-full h-1 appearance-none bg-slate-200 rounded-full pointer-events-none z-[3] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-blue-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:border-[2.5px] [&::-moz-range-thumb]:border-blue-500"
              />
              <input
                type="range"
                min={dateBounds.dateMin}
                max={dateBounds.dateMax}
                step={86400000}
                value={dateRange[1] < Infinity ? dateRange[1] : dateBounds.dateMax}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const minVal = dateRange[0] > 0 ? dateRange[0] : dateBounds.dateMin;
                  onDateRangeChange([dateRange[0], Math.max(val, minVal)]);
                }}
                className="absolute w-full h-1 appearance-none bg-transparent rounded-full pointer-events-none z-[4] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-blue-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:border-[2.5px] [&::-moz-range-thumb]:border-blue-500"
              />
            </div>
          ) : (
            <span className="text-xs text-slate-400 mt-2 block">Jeden punkt na osi czasu</span>
          )}
        </div>

        {/* Price slider */}
        <div className="flex-1">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider flex items-center gap-1.5">
              Cena katalogowa łączna (+opcje) brutto
            </span>
            <span className="text-xs text-slate-700 tabular-nums font-bold">
              {formatPrice(priceRange[0] > 0 ? priceRange[0] : priceBounds.priceMin)}
              {" — "}
              {formatPrice(priceRange[1] < Infinity ? priceRange[1] : priceBounds.priceMax)}
            </span>
          </div>
          
          {priceSpan > 0 ? (
            <div className="relative h-6 flex items-center mt-1">
              <input
                type="range"
                min={priceBounds.priceMin}
                max={priceBounds.priceMax}
                step={1000} 
                value={priceRange[0] > 0 ? priceRange[0] : priceBounds.priceMin}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const maxVal = priceRange[1] < Infinity ? priceRange[1] : priceBounds.priceMax;
                  onPriceRangeChange([Math.min(val, maxVal), priceRange[1]]);
                }}
                className={`absolute w-full h-1 appearance-none bg-slate-200 rounded-full pointer-events-none z-[3] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-slate-700 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer`}
              />
              <input
                type="range"
                min={priceBounds.priceMin}
                max={priceBounds.priceMax}
                step={1000}
                value={priceRange[1] < Infinity ? priceRange[1] : priceBounds.priceMax}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const minVal = priceRange[0] > 0 ? priceRange[0] : priceBounds.priceMin;
                  onPriceRangeChange([priceRange[0], Math.max(val, minVal)]);
                }}
                className={`absolute w-full h-1 appearance-none bg-transparent rounded-full pointer-events-none z-[4] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-slate-700 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer`}
              />
            </div>
          ) : (
            <span className="text-xs text-slate-400 mt-2 block">Brak zróżnicowania cen</span>
          )}
        </div>

        {/* Power slider */}
        <div className="flex-1">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" /> Moc (KM)
            </span>
            <span className="text-xs text-slate-700 tabular-nums font-bold">
              {powerRange[0] > 0 ? powerRange[0] : powerBounds.powerMin}
              {" — "}
              {powerRange[1] < Infinity ? powerRange[1] : powerBounds.powerMax} KM
            </span>
          </div>
          
          {powerSpan > 0 ? (
            <div className="relative h-6 flex items-center mt-1">
              <input
                type="range"
                min={powerBounds.powerMin}
                max={powerBounds.powerMax}
                step={5}
                value={powerRange[0] > 0 ? powerRange[0] : powerBounds.powerMin}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const maxVal = powerRange[1] < Infinity ? powerRange[1] : powerBounds.powerMax;
                  onPowerRangeChange([Math.min(val, maxVal), powerRange[1]]);
                }}
                className={`absolute w-full h-1 appearance-none bg-slate-200 rounded-full pointer-events-none z-[3] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-red-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer`}
              />
              <input
                type="range"
                min={powerBounds.powerMin}
                max={powerBounds.powerMax}
                step={5}
                value={powerRange[1] < Infinity ? powerRange[1] : powerBounds.powerMax}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const minVal = powerRange[0] > 0 ? powerRange[0] : powerBounds.powerMin;
                  onPowerRangeChange([powerRange[0], Math.max(val, minVal)]);
                }}
                className={`absolute w-full h-1 appearance-none bg-transparent rounded-full pointer-events-none z-[4] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-red-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer`}
              />
            </div>
          ) : (
            <span className="text-xs text-slate-400 mt-2 block">Brak zróżnicowania mocy</span>
          )}
        </div>

        {/* Koszt dzienny slider */}
        {(() => {
          const kdSpan = kosztDziennyBounds.kosztDziennyMax - kosztDziennyBounds.kosztDziennyMin;
          return (
            <div className="flex-1">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider">
                  Koszt dzienny
                </span>
                <span className="text-xs text-slate-700 tabular-nums font-bold">
                  {kosztDziennyRange[0] > 0 ? kosztDziennyRange[0] : kosztDziennyBounds.kosztDziennyMin}
                  {" — "}
                  {kosztDziennyRange[1] < Infinity ? kosztDziennyRange[1] : kosztDziennyBounds.kosztDziennyMax} PLN/d
                </span>
              </div>
              {kdSpan > 0 ? (
                <div className="relative h-6 flex items-center mt-1">
                  <input
                    type="range"
                    min={kosztDziennyBounds.kosztDziennyMin}
                    max={kosztDziennyBounds.kosztDziennyMax}
                    step={1}
                    value={kosztDziennyRange[0] > 0 ? kosztDziennyRange[0] : kosztDziennyBounds.kosztDziennyMin}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      const maxVal = kosztDziennyRange[1] < Infinity ? kosztDziennyRange[1] : kosztDziennyBounds.kosztDziennyMax;
                      onKosztDziennyRangeChange([Math.min(val, maxVal), kosztDziennyRange[1]]);
                    }}
                    className="absolute w-full h-1 appearance-none bg-slate-200 rounded-full pointer-events-none z-[3] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-emerald-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer"
                  />
                  <input
                    type="range"
                    min={kosztDziennyBounds.kosztDziennyMin}
                    max={kosztDziennyBounds.kosztDziennyMax}
                    step={1}
                    value={kosztDziennyRange[1] < Infinity ? kosztDziennyRange[1] : kosztDziennyBounds.kosztDziennyMax}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      const minVal = kosztDziennyRange[0] > 0 ? kosztDziennyRange[0] : kosztDziennyBounds.kosztDziennyMin;
                      onKosztDziennyRangeChange([kosztDziennyRange[0], Math.max(val, minVal)]);
                    }}
                    className="absolute w-full h-1 appearance-none bg-transparent rounded-full pointer-events-none z-[4] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[2.5px] [&::-webkit-slider-thumb]:border-emerald-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer"
                  />
                </div>
              ) : (
                <span className="text-xs text-slate-400 mt-2 block">
                  {kosztDziennyBounds.kosztDziennyMin === 0 ? "Brak danych kosztowych" : "Jeden punkt kosztowy"}
                </span>
              )}
            </div>
          );
        })()}
      </div>}

      {/* Row 4: Selection bar (only when items exist) */}
      {totalVisible > 0 && (
        <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-4 py-2.5 shadow-sm mt-4">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <div
              onClick={onToggleSelectAll}
              className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors cursor-pointer ${
                allVisibleSelected
                  ? "bg-blue-500 border-blue-500"
                  : selectedCount > 0
                    ? "bg-blue-100 border-blue-300"
                    : "border-slate-300 hover:border-blue-400"
              }`}
            >
              {allVisibleSelected && (
                <Check className="w-3 h-3 text-white" />
              )}
            </div>
            <span className="text-xs text-slate-600 font-medium">
              {selectedCount > 0
                ? `Zaznaczono ${selectedCount} z ${totalVisible}`
                : `Zaznacz całą listę widoczną z filtru (${totalVisible})`}
            </span>
          </label>

          {selectedCount > 0 && (
            <>
              <div className="w-px h-5 bg-slate-200" />
              <button
                onClick={onDeleteSelected}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs uppercase font-bold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-100 rounded-md transition-colors"
                title="Skasuj pojazd(y) i załączniki PDF/XLS z bazy i Cloud Storage"
              >
                <Trash2 className="w-3 h-3" />
                Usuń Dokument z Ekstrakcją ({selectedCount})
              </button>

              {selectedCount >= 2 && selectedCount <= 5 && (
                <button
                  onClick={onCompareSelected}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs uppercase font-bold text-slate-700 hover:text-blue-700 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-md transition-colors"
                >
                  <GitCompareArrows className="w-3 h-3" />
                  Porównaj ({selectedCount})
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
