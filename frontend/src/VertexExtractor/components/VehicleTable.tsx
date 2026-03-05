import { useEffect, useState } from "react";
import { Database, Info, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { cn } from "../../lib/utils";
import type { FleetVehicleView } from "../types";
import { VehicleRowCard } from "./VehicleTableParts/VehicleRowCard";
import { VehicleFilterBar } from "./VehicleTableParts/VehicleFilterBar";
import { VehicleComparisonModal } from "./VehicleComparisonModal";
import { useVehicleFilters } from "../hooks/useVehicleFilters";
import { useVehicleSelection } from "../hooks/useVehicleSelection";
import { useDiscountAlerts } from "../hooks/useDiscountAlerts";

interface VehicleTableProps {
  savedVehicles: FleetVehicleView[];
  isLoadingSaved: boolean;
  globalSearchQuery: string;
  isSearching: boolean;
  setGlobalSearchQuery: (query: string) => void;
  handleGlobalSearch: (e: React.FormEvent) => void;
  fetchSavedVehicles: () => void;
  handleOpenSavedJson: (vehicleId: string, titleName: string) => void;
  handleDeleteVehicle?: (vehicleId: string) => void;
}

export function VehicleTable({
  savedVehicles,
  isLoadingSaved,
  globalSearchQuery,
  isSearching,
  setGlobalSearchQuery,
  handleGlobalSearch,
  fetchSavedVehicles,
  handleOpenSavedJson,
  handleDeleteVehicle,
}: VehicleTableProps) {
  const {
    filters,
    bounds,
    activeDateRange,
    filteredVehicles,
    setSortKey,
    setDateRange,
    setLiveSearchText,
    resetFilters,
  } = useVehicleFilters(savedVehicles);

  const {
    selectedCount,
    toggleSelect,
    selectAll,
    deselectAll,
    isSelected,
    getSelectedVehicles,
  } = useVehicleSelection(filteredVehicles);

  const discountAlerts = useDiscountAlerts(savedVehicles);
  const [showComparison, setShowComparison] = useState(false);

  // Listen for the custom event from the nested card
  useEffect(() => {
    const handleCustomDelete = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (
        customEvent.detail &&
        customEvent.detail.vehicleId &&
        handleDeleteVehicle
      ) {
        handleDeleteVehicle(customEvent.detail.vehicleId);
      }
    };
    window.addEventListener("deleteVehicle", handleCustomDelete);
    return () => {
      window.removeEventListener("deleteVehicle", handleCustomDelete);
    };
  }, [handleDeleteVehicle]);

  const handleDeleteSelected = async () => {
    const selected = getSelectedVehicles();
    if (selected.length === 0) return;

    const confirmed = window.confirm(
      `Czy na pewno chcesz usunąć ${selected.length} rekordów? Tej operacji nie można cofnąć.`,
    );
    if (!confirmed) return;

    try {
      const baseUrl =
        import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(
        `${baseUrl}/api/delete-vehicles-batch`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            vehicle_ids: selected.map((v) => v.id),
          }),
        },
      );

      if (!response.ok) throw new Error("Batch delete failed");

      deselectAll();
      fetchSavedVehicles();
    } catch (err) {
      console.error("Batch delete error:", err);
      alert("Wystąpił błąd podczas usuwania rekordów.");
    }
  };

  const handleCompareSelected = () => {
    if (selectedCount >= 2 && selectedCount <= 5) {
      setShowComparison(true);
    }
  };

  const allVisibleIds = filteredVehicles.map((v) => v.id);
  const allVisibleSelected =
    filteredVehicles.length > 0 &&
    allVisibleIds.every((id) => isSelected(id));



  return (
    <div className="w-full">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
        <div>
          <h2 className="text-lg font-medium text-slate-900 tracking-tight">
            Przetworzone pojazdy
          </h2>
          <p className="text-xs text-slate-500 mt-1 flex items-center">
            <Info className="w-3 h-3 mr-1" />
            Baza zsynchronizowana z modelem
            <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded ml-1 font-mono text-xs font-semibold border border-blue-100">
              v2.0_digital_twin
            </span>
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <form
            onSubmit={handleGlobalSearch}
            className="relative flex-1 min-w-[280px]"
          >
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <input
              type="text"
              value={globalSearchQuery}
              onChange={(e) => setGlobalSearchQuery(e.target.value)}
              placeholder="Wyszukaj z użyciem AI (Gemini)..."
              className="w-full pl-9 pr-20 py-2.5 border border-slate-200 bg-white rounded-lg text-sm outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all shadow-sm"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs uppercase font-bold text-slate-600 hover:text-blue-600 px-3 py-1.5 rounded-md bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 transition-colors disabled:opacity-50"
            >
              {isSearching ? (
                <Loader2 className="w-3 h-3 animate-spin mx-auto" />
              ) : (
                "Szukaj"
              )}
            </button>
          </form>

          <button
            onClick={fetchSavedVehicles}
            className="p-2.5 text-slate-400 hover:text-blue-600 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-100 shadow-sm rounded-lg transition-all"
            title="Odśwież listę"
          >
            <RefreshCw
              className={cn(
                "w-4 h-4",
                isLoadingSaved && "animate-spin text-blue-500",
              )}
            />
          </button>
        </div>
      </div>

      {isLoadingSaved && savedVehicles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-white rounded-2xl border border-dashed border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
          <p className="text-sm font-medium text-slate-600">
            Wczytywanie floty...
          </p>
        </div>
      ) : savedVehicles.length === 0 ? (
        <div className="border border-dashed border-slate-300 bg-slate-50 rounded-2xl p-16 text-center flex flex-col items-center justify-center shadow-inner">
          <Database className="w-10 h-10 text-slate-300 mb-4" />
          <p className="text-slate-700 text-base font-semibold">
            Brak wyekstrahowanych dokumentów.
          </p>
          <p className="text-sm text-slate-500 mt-2 max-w-sm">
            Prześlij nowe oferty i cenniki powyżej, aby automatycznie
            utworzyć z nich ustrukturyzowane wpisy.
          </p>
        </div>
      ) : (
        <>
          {/* Filter bar */}
          <VehicleFilterBar
            sortKey={filters.sortKey}
            sortDir={filters.sortDir}
            onSortKeyChange={setSortKey}
            liveSearchText={filters.liveSearchText}
            onLiveSearchChange={setLiveSearchText}
            dateRange={activeDateRange}
            dateBounds={{
              dateMin: bounds.dateMin,
              dateMax: bounds.dateMax,
            }}
            onDateRangeChange={setDateRange}
            onResetFilters={resetFilters}
            selectedCount={selectedCount}
            totalVisible={filteredVehicles.length}
            allVisibleSelected={allVisibleSelected}
            onToggleSelectAll={() => selectAll(allVisibleIds)}
            onDeleteSelected={handleDeleteSelected}
            onCompareSelected={handleCompareSelected}
          />

          {/* Vehicle list */}
          <div className="flex flex-col gap-4">
            <style
              dangerouslySetInnerHTML={{
                __html: `
              .custom-scrollbar::-webkit-scrollbar { width: 6px; }
              .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
              .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 10px; }
              .custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #94a3b8; }
            `,
              }}
            />

            {filteredVehicles.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <p className="text-sm font-medium">
                  Brak wyników spełniających kryteria filtrów.
                </p>
                <button
                  onClick={resetFilters}
                  className="mt-2 text-xs text-blue-500 hover:text-blue-700 underline"
                >
                  Resetuj filtry
                </button>
              </div>
            ) : (
              filteredVehicles.map((vehicle) => (
                <VehicleRowCard
                  key={vehicle.id}
                  vehicle={vehicle}
                  handleOpenSavedJson={handleOpenSavedJson}
                  onRefresh={fetchSavedVehicles}
                  isSelected={isSelected(vehicle.id)}
                  onToggleSelect={() => toggleSelect(vehicle.id)}
                  crossCardAlerts={discountAlerts.get(vehicle.id)}
                />
              ))
            )}
          </div>
        </>
      )}

      {/* Comparison Modal */}
      {showComparison && (
        <VehicleComparisonModal
          vehicles={getSelectedVehicles()}
          onClose={() => setShowComparison(false)}
        />
      )}
    </div>
  );
}
