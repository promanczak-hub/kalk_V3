import { useEffect, useState, useRef } from "react";
import { Database, Info, RefreshCw, Sparkles } from "lucide-react";
import Skeleton from "@mui/material/Skeleton";
import { cn } from "../../lib/utils";
import type { FleetVehicleView } from "../types";
import { VehicleRowCard } from "./VehicleTableParts/VehicleRowCard";
import { VehicleFilterBar } from "./VehicleTableParts/VehicleFilterBar";
import { VehicleComparisonModal } from "./VehicleComparisonModal";
import { useVehicleFilters } from "../hooks/useVehicleFilters";
import { useVehicleSelection } from "../hooks/useVehicleSelection";
import { useDiscountAlerts } from "../hooks/useDiscountAlerts";
import { apiClient } from '../../lib/apiClient';
import { ConfirmModal } from "../../components/ConfirmModal";
import type { ControlCenterSettings } from "../../hooks/useCalculator";
import Pagination from "@mui/material/Pagination";

interface VehicleTableProps {
  savedVehicles: FleetVehicleView[];
  isLoadingSaved: boolean;
  globalSearchQuery: string;
  isSearching: boolean;
  setGlobalSearchQuery: (query: string) => void;
  handleGlobalSearch: (e: React.FormEvent) => void;
  liveSearchText: string;
  setLiveSearchText: (query: string) => void;
  fetchSavedVehicles: () => void;
  handleOpenSavedJson: (vehicleId: string, titleName: string) => void;
  handleDeleteVehicle?: (vehicleId: string) => void;
  globalSettings?: ControlCenterSettings | null;
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  totalCount: number;
  highlightVehicleId?: string | null;
  bodyTypes?: any[];
  paintTypes?: any[];
}

export function VehicleTable({
  savedVehicles,
  isLoadingSaved,
  globalSearchQuery: _globalSearchQuery,
  isSearching: _isSearching,
  setGlobalSearchQuery: _setGlobalSearchQuery,
  handleGlobalSearch: _handleGlobalSearch,
  liveSearchText,
  setLiveSearchText,
  fetchSavedVehicles,
  handleOpenSavedJson,
  handleDeleteVehicle,
  globalSettings,
  page,
  setPage,
  pageSize,
  totalCount,
  highlightVehicleId,
  bodyTypes,
  paintTypes,
}: VehicleTableProps) {
  const {
    filters,
    bounds,
    activeDateRange,
    filteredVehicles,
    setSortKey,
    setDateRange,
    setShowUnmappedSamarOnly,
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
  const scrollAttemptedRef = useRef(false);

  // Scroll to highlighted vehicle once data has loaded
  useEffect(() => {
    if (!highlightVehicleId || isLoadingSaved || scrollAttemptedRef.current) return;
    // Try up to 10 times (500ms apart) to find the element after render
    let attempts = 0;
    const tryScroll = () => {
      const el = document.getElementById(`vehicle-row-${highlightVehicleId}`);
      if (el) {
        scrollAttemptedRef.current = true;
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      } else if (attempts < 10) {
        attempts++;
        setTimeout(tryScroll, 300);
      }
    };
    tryScroll();
  }, [highlightVehicleId, isLoadingSaved, savedVehicles]);

  const [vehicleToDelete, setVehicleToDelete] = useState<string | null>(null);
  const [isBatchDeleteModalOpen, setIsBatchDeleteModalOpen] = useState(false);

  // Listen for the custom event from the nested card
  useEffect(() => {
    const handleCustomDelete = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail && customEvent.detail.vehicleId) {
        setVehicleToDelete(customEvent.detail.vehicleId);
      }
    };
    window.addEventListener("deleteVehicle", handleCustomDelete);
    return () => {
      window.removeEventListener("deleteVehicle", handleCustomDelete);
    };
  }, []);

  const handleDeleteSelected = async () => {
    const selected = getSelectedVehicles();
    if (selected.length === 0) return;

    try {
      const response = await apiClient.fetch(`/api/delete-vehicles-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_ids: selected.map((v) => v.id),
        }),
      });

      if (!response.ok) throw new Error("Batch delete failed");

      // Optymistyczne ukrycie z widoku zeby nie polegać podwójnie na widoku i pobraniu (ghost)
      deselectAll();
      fetchSavedVehicles();
    } catch (err) {
      console.error("Batch delete error:", err);
      alert("Wystąpił błąd podczas usuwania rekordów.");
    } finally {
      setIsBatchDeleteModalOpen(false);
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
          <div className="text-xs text-slate-500 mt-1 flex flex-col sm:flex-row sm:items-center gap-2">
            <span className="flex items-center">
              <Info className="w-3 h-3 mr-1" />
              Baza zsynchronizowana z modelem
              <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded ml-1 font-mono text-xs font-semibold border border-blue-100">
                v2.0_digital_twin
              </span>
            </span>
            {totalCount > 0 && (
              <span className="text-slate-400">
                (Łącznie w bazie: <strong className="text-slate-700">{totalCount}</strong> rekordów)
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <form
            onSubmit={(e) => e.preventDefault()}
            className="relative flex-1 min-w-[280px]"
            title="Wyszukiwanie AI — wkrótce dostępne"
          >
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <input
              type="text"
              disabled
              placeholder="Wyszukaj z użyciem AI (Gemini)... — wkrótce"
              className="w-full pl-9 pr-24 py-2.5 border border-slate-200 bg-slate-50 rounded-lg text-sm outline-none cursor-not-allowed text-slate-400 shadow-sm"
            />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] uppercase font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded border border-amber-200">
              Wkrótce
            </span>
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
        <div className="flex flex-col gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-5 animate-fadeUp" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <Skeleton variant="text" width={220} height={28} />
                  <Skeleton variant="text" width={320} height={18} sx={{ mt: 0.5 }} />
                  <div className="flex gap-2 mt-2">
                    <Skeleton variant="rounded" width={80} height={24} />
                    <Skeleton variant="rounded" width={60} height={24} />
                    <Skeleton variant="rounded" width={100} height={24} />
                  </div>
                </div>
                <Skeleton variant="rounded" width={140} height={60} />
              </div>
            </div>
          ))}
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
            liveSearchText={liveSearchText}
            onLiveSearchChange={setLiveSearchText}
            dateRange={activeDateRange}
            dateBounds={{
              dateMin: bounds.dateMin,
              dateMax: bounds.dateMax,
            }}
            onDateRangeChange={setDateRange}
            showUnmappedSamarOnly={filters.showUnmappedSamarOnly}
            onShowUnmappedSamarChange={setShowUnmappedSamarOnly}
            onResetFilters={resetFilters}
            selectedCount={selectedCount}
            totalVisible={filteredVehicles.length}
            allVisibleSelected={allVisibleSelected}
            onToggleSelectAll={() => selectAll(allVisibleIds)}
            onDeleteSelected={() => setIsBatchDeleteModalOpen(true)}
            onCompareSelected={handleCompareSelected}
          />

          {/* Vehicle list */}
          <div className="flex flex-col gap-4 stagger-children">
            {totalCount > pageSize && (
              <div className="flex justify-center my-2">
                <Pagination
                  count={Math.ceil(totalCount / pageSize)}
                  page={page}
                  onChange={(_, val) => {
                    setPage(val);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  color="primary"
                />
              </div>
            )}

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
                  globalSettings={globalSettings}
                  bodyTypes={bodyTypes}
                  paintTypes={paintTypes}
                  isHighlighted={vehicle.id === highlightVehicleId}
                />
              ))
            )}

            {totalCount > pageSize && filteredVehicles.length > 0 && (
              <div className="flex justify-center mt-6 mb-2">
                <Pagination
                  count={Math.ceil(totalCount / pageSize)}
                  page={page}
                  onChange={(_, val) => {
                    setPage(val);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  color="primary"
                />
              </div>
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

      {/* Confirm Modals */}
      <ConfirmModal
        isOpen={!!vehicleToDelete}
        title="Usuwanie rekordu"
        message="Czy na pewno chcesz trwale usunąć ten rekord powiązany z dokumentem? Tej operacji nie można cofnąć."
        confirmText="Usuń"
        onConfirm={() => {
          if (vehicleToDelete && handleDeleteVehicle) {
            handleDeleteVehicle(vehicleToDelete);
          }
          setVehicleToDelete(null);
        }}
        onCancel={() => setVehicleToDelete(null)}
      />

      <ConfirmModal
        isOpen={isBatchDeleteModalOpen}
        title="Usuwanie zaznaczonych"
        message={`Czy na pewno chcesz trwale usunąć ${selectedCount} rekordów? Tej operacji nie można cofnąć.`}
        confirmText="Usuń"
        onConfirm={handleDeleteSelected}
        onCancel={() => setIsBatchDeleteModalOpen(false)}
      />
    </div>
  );
}

