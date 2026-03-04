import { useEffect } from "react";
import { Database, Info, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { cn } from "./ui/DocumentCard";
import type { FleetVehicleView } from "../types";
import { VehicleRowCard } from "./VehicleTableParts/VehicleRowCard";

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
  // Listen for the custom event from the nested card
  useEffect(() => {
    const handleCustomDelete = (e: Event) => {
        const customEvent = e as CustomEvent;
        if (customEvent.detail && customEvent.detail.vehicleId && handleDeleteVehicle) {
            handleDeleteVehicle(customEvent.detail.vehicleId);
        }
    };
    window.addEventListener('deleteVehicle', handleCustomDelete);
    return () => {
        window.removeEventListener('deleteVehicle', handleCustomDelete);
    };
  }, [handleDeleteVehicle]);

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
            <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded ml-1 font-mono text-[10px] font-semibold border border-blue-100">
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
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[10px] uppercase font-bold text-slate-600 hover:text-blue-600 px-3 py-1.5 rounded-md bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 transition-colors disabled:opacity-50"
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
          <p className="text-sm font-medium text-slate-600">Wczytywanie floty...</p>
        </div>
      ) : savedVehicles.length === 0 ? (
        <div className="border border-dashed border-slate-300 bg-slate-50 rounded-2xl p-16 text-center flex flex-col items-center justify-center shadow-inner">
          <Database className="w-10 h-10 text-slate-300 mb-4" />
          <p className="text-slate-700 text-base font-semibold">Brak wyekstrahowanych dokumentów.</p>
          <p className="text-sm text-slate-500 mt-2 max-w-sm">
            Prześlij nowe oferty i cenniki powyżej, aby automatycznie utworzyć z nich ustrukturyzowane wpisy.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <style dangerouslySetInnerHTML={{__html: `
            .custom-scrollbar::-webkit-scrollbar { width: 6px; }
            .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
            .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 10px; }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #94a3b8; }
          `}} />
          {savedVehicles.map((vehicle) => (
            <VehicleRowCard
              key={vehicle.id}
              vehicle={vehicle}
              handleOpenSavedJson={handleOpenSavedJson}
              onRefresh={fetchSavedVehicles}
            />
          ))}
        </div>
      )}
    </div>
  );
}
