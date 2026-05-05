import { useEffect, useState, useRef } from "react";
import { Database, Info, RefreshCw } from "lucide-react";
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
import type { ControlCenterSettings } from "../../types";
import Pagination from "@mui/material/Pagination";

interface VehicleTableProps {
  savedVehicles: FleetVehicleView[];
  isLoadingSaved: boolean;

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
  bodyTypes?: { id: number; name: string; vehicle_class: string; }[];
  paintTypes?: { id: number; name: string; [key: string]: unknown; }[];
  driveTypes?: string[];
  transmissionTypes?: string[];
}

export function VehicleTable({
  savedVehicles,
  isLoadingSaved,

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
  driveTypes,
  transmissionTypes,
}: VehicleTableProps) {
  const {
    filters,
    aggregates,
    activeDateRange,
    activePriceRange,
    currentModePriceMin,
    currentModePriceMax,
    filteredVehicles,
    setSortKey,
    setDateRange,
    setPriceRange,
    setSelectedBrands,
    setSelectedFuels,
    setSelectedSamarClasses,
    setShowUnmappedSamarOnly,
    resetFilters,
    activePowerRange,
    activeKosztDziennyRange,
    setSelectedBodyTypes,
    setSelectedTransmissions,
    setSelectedDrives,
    setPowerRange,
    setKosztDziennyRange,
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
              Baza pojazdów zaimportowanych z cenników PDF/XLS
            </span>
            {totalCount > 0 && (
              <span className="text-slate-400">
                (Łącznie w bazie: <strong className="text-slate-700">{totalCount}</strong> rekordów)
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">


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
              dateMin: aggregates.dateMin,
              dateMax: aggregates.dateMax,
            }}
            onDateRangeChange={setDateRange}

            priceRange={activePriceRange}
            priceBounds={{
              priceMin: currentModePriceMin,
              priceMax: currentModePriceMax,
            }}
            onPriceRangeChange={setPriceRange}

            availableBrands={aggregates.brands}
            selectedBrands={filters.selectedBrands}
            onSelectedBrandsChange={setSelectedBrands}

            availableFuels={aggregates.fuels}
            selectedFuels={filters.selectedFuels}
            onSelectedFuelsChange={setSelectedFuels}

            availableSamarClasses={aggregates.samarClasses}
            selectedSamarClasses={filters.selectedSamarClasses}
            onSelectedSamarClassesChange={setSelectedSamarClasses}

            availableBodyTypes={aggregates.bodyTypes}
            selectedBodyTypes={filters.selectedBodyTypes}
            onSelectedBodyTypesChange={setSelectedBodyTypes}

            availableTransmissions={aggregates.transmissions}
            selectedTransmissions={filters.selectedTransmissions}
            onSelectedTransmissionsChange={setSelectedTransmissions}

            availableDrives={aggregates.drives}
            selectedDrives={filters.selectedDrives}
            onSelectedDrivesChange={setSelectedDrives}

            powerRange={activePowerRange}
            powerBounds={{ powerMin: aggregates.powerMin, powerMax: aggregates.powerMax }}
            onPowerRangeChange={setPowerRange}

            kosztDziennyRange={activeKosztDziennyRange}
            kosztDziennyBounds={{ kosztDziennyMin: aggregates.kosztDziennyMin, kosztDziennyMax: aggregates.kosztDziennyMax }}
            onKosztDziennyRangeChange={setKosztDziennyRange}

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
                  driveTypes={driveTypes}
                  transmissionTypes={transmissionTypes}
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

