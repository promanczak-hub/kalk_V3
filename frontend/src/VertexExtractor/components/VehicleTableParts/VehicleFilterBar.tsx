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
} from "lucide-react";
import { format } from "date-fns";
import type { SortKey, SortDir } from "../../hooks/useVehicleFilters";

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



export function VehicleFilterBar({
  sortKey,
  sortDir,
  onSortKeyChange,
  liveSearchText,
  onLiveSearchChange,
  dateRange,
  dateBounds,
  onDateRangeChange,
  onResetFilters,
  selectedCount,
  totalVisible,
  allVisibleSelected,
  onToggleSelectAll,
  onDeleteSelected,
  onCompareSelected,
}: VehicleFilterBarProps) {
  const [localSearch, setLocalSearch] = useState(liveSearchText);
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
    dateRange[0] > 0 ||
    dateRange[1] < Infinity;

  const dateSpan = dateBounds.dateMax - dateBounds.dateMin;

  return (
    <div className="space-y-3 mb-5">
      {/* Row 1: Sort + Live search */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Sort dropdown */}
        <div className="flex items-center gap-1.5">
          <label className="text-xs uppercase font-semibold text-slate-500 tracking-wider whitespace-nowrap">
            Sortuj:
          </label>
          <div className="flex items-center bg-white border border-slate-200 rounded-lg shadow-sm">
            <select
              value={sortKey}
              onChange={(e) => onSortKeyChange(e.target.value as SortKey)}
              className="text-xs text-slate-700 bg-transparent pl-2.5 pr-1 py-2 outline-none cursor-pointer font-medium"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
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

        {/* Live search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={localSearch}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Filtruj: klima, tapicerka, xenon..."
            className="w-full pl-8 pr-8 py-2 border border-slate-200 bg-white rounded-lg text-xs outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-50 transition-all shadow-sm"
          />
          {localSearch && (
            <button
              onClick={() => handleSearchInput("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-500"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {hasActiveFilters && (
          <button
            onClick={onResetFilters}
            className="flex items-center gap-1.5 px-3 py-2 text-xs uppercase font-bold text-slate-500 hover:text-blue-600 bg-white hover:bg-blue-50 border border-slate-200 rounded-lg shadow-sm transition-colors whitespace-nowrap"
            title="Resetuj filtry"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        )}
      </div>

      {/* Row 2: Date slider + Price slider */}
      <div className="flex flex-col sm:flex-row gap-4 bg-slate-50/50 border border-slate-100 rounded-lg px-4 py-3">
        {/* Date range slider */}
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider flex items-center gap-1">
              <Calendar className="w-3 h-3" /> Data oferty
            </span>
            <span className="text-xs text-slate-500 tabular-nums font-medium">
              {format(new Date(dateRange[0] > 0 ? dateRange[0] : dateBounds.dateMin), "dd.MM.yyyy")}
              {" — "}
              {format(new Date(dateRange[1] < Infinity ? dateRange[1] : dateBounds.dateMax), "dd.MM.yyyy")}
            </span>
          </div>
          {dateSpan > 0 ? (
            <div className="relative h-5 flex items-center">
              <input
                type="range"
                min={dateBounds.dateMin}
                max={dateBounds.dateMax}
                step={86400000}
                value={dateRange[0] > 0 ? dateRange[0] : dateBounds.dateMin}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  const maxVal = dateRange[1] < Infinity ? dateRange[1] : dateBounds.dateMax;
                  onDateRangeChange([Math.min(val, maxVal), dateRange[1]]);
                }}
                className="absolute w-full h-1 appearance-none bg-slate-200 rounded-full pointer-events-none z-[3] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-blue-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer"
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
                className="absolute w-full h-1 appearance-none bg-transparent rounded-full pointer-events-none z-[4] [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-blue-500 [&::-webkit-slider-thumb]:shadow [&::-webkit-slider-thumb]:appearance-none [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:cursor-pointer"
              />
            </div>
          ) : (
            <span className="text-xs text-slate-400">Jedna data</span>
          )}
        </div>
      </div>

      {/* Row 3: Selection bar (only when items exist) */}
      {totalVisible > 0 && (
        <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-4 py-2.5 shadow-sm">
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
            <span className="text-xs text-slate-600">
              {selectedCount > 0
                ? `Zaznaczono ${selectedCount} z ${totalVisible}`
                : `Zaznacz wszystkie (${totalVisible})`}
            </span>
          </label>

          {selectedCount > 0 && (
            <>
              <div className="w-px h-5 bg-slate-200" />
              <button
                onClick={onDeleteSelected}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs uppercase font-bold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-100 rounded-md transition-colors"
              >
                <Trash2 className="w-3 h-3" />
                Usuń ({selectedCount})
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
