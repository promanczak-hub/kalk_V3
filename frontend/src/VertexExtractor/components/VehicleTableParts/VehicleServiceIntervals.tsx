import { Loader2, Wrench } from "lucide-react";
import type { FleetVehicleView } from "../../types";

interface VehicleServiceIntervalsProps {
  vehicle: FleetVehicleView;
  serviceKm: number | "";
  setServiceKm: (val: number | "") => void;
  serviceMonths: number | "";
  setServiceMonths: (val: number | "") => void;
  handleSaveServiceInterval: () => void;
  isSavingInterval: boolean;
}

export function VehicleServiceIntervals({
  vehicle,
  serviceKm,
  setServiceKm,
  serviceMonths,
  setServiceMonths,
  handleSaveServiceInterval,
  isSavingInterval,
}: VehicleServiceIntervalsProps) {
  return (
    <div>
      <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
        <Wrench className="w-4 h-4 mr-2" />
        Cykl Serwisowy (Przeglądy)
      </h4>
      <div className="bg-white rounded border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="flex flex-col flex-1 mr-4">
          <span className="text-[11px] font-bold text-slate-800 uppercase mb-2">Dystans / Czas</span>
          <div className="flex items-center gap-2">
            <input 
              type="number" 
              value={serviceKm} 
              onChange={(e) => setServiceKm(e.target.value === "" ? "" : Number(e.target.value))}
              placeholder="np. 30000"
              className="w-24 px-2 py-1 text-sm border border-slate-200 rounded text-slate-700 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium text-right transition-colors" 
            />
            <span className="text-sm font-medium text-slate-500">km</span>
            <span className="mx-1 text-slate-300">/</span>
            <input 
              type="number" 
              step="any"
              value={serviceMonths === "" ? "" : Number(serviceMonths) / 12} 
              onChange={(e) => setServiceMonths(e.target.value === "" ? "" : Number(e.target.value) * 12)}
              placeholder="np. 2"
              className="w-16 px-2 py-1 text-sm border border-slate-200 rounded text-slate-700 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium text-center transition-colors" 
            />
            <span className="text-sm font-medium text-slate-500">lata</span>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-2">
          {(!vehicle.service_interval_km || !vehicle.service_interval_months) && (
             <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded border border-amber-200 whitespace-nowrap hidden sm:inline-block">
               Brak pełnych danych
             </span>
          )}
          {(serviceKm !== (vehicle.service_interval_km ?? "") || serviceMonths !== (vehicle.service_interval_months ?? "")) && (
            <button 
               onClick={handleSaveServiceInterval}
               disabled={isSavingInterval}
               className="flex items-center text-xs font-semibold px-3 py-1.5 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-100 transition-colors disabled:opacity-50"
            >
               {isSavingInterval ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
               {isSavingInterval ? "Zapis..." : "Zapisz cykl"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
