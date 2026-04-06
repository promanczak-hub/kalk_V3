import { useState, useEffect } from "react";
import { Loader2, History, Copy, Clock, CarFront, FileText, ChevronRight, Check, X, Shield, Wrench, Settings } from "lucide-react";
import { cn } from "../../../lib/utils";
import { apiClient } from "../../../lib/apiClient";
import { fmtPLN } from "./calculations/calculations.utils";
import { API_BASE_URL } from "../../../config/env";

export interface TogglesSummary {
  include_tires: boolean;
  include_insurance: boolean;
  include_service: boolean;
  include_replacement_car: boolean;
}

export interface HistoricalCalculation {
  id: string;
  numer_kalkulacji: string;
  status: string;
  source: string;
  dane_pojazdu: string;
  cena_netto: number;
  created_at: string;
  updated_at: string;
  body_type: string | null;
  fuel: string | null;
  discount_pct: number | null;
  options_count: number;
  toggles_summary?: TogglesSummary | null;
  rata_netto?: number | null;
  matrix_count?: number;
}

interface VehicleCalculationsListProps {
  vehicleId: string;
  activeKalkulacjaId?: string | null;
  onSelect: (kalkulacjaId: string, numerKalkulacji: string) => void;
  // This is used for creating a new clone based on selected calculation
  onClone?: (kalkulacjaId: string) => void;
}

// Helper for rendering toggle badges
const ConfigBadge = ({ label, enabled, icon: Icon }: { label: string; enabled: boolean; icon: React.ElementType }) => (
  <div 
    className={cn(
      "flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] whitespace-nowrap",
      enabled ? "bg-emerald-50 text-emerald-700 font-medium" : "bg-slate-50 text-slate-400"
    )}
  >
    <Icon className="w-3 h-3" />
    <span className="hidden sm:inline">{label}</span>
    {enabled ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 opacity-50" />}
  </div>
);

export function VehicleCalculationsList({
  vehicleId,
  activeKalkulacjaId,
  onSelect,
  onClone
}: VehicleCalculationsListProps) {
  const [items, setItems] = useState<HistoricalCalculation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.fetch(`${API_BASE_URL}/api/kalkulacje/vehicle/${vehicleId}`);
      if (!res.ok) throw new Error("Błąd pobierania historii kalkulacji");
      const data = await res.json();
      setItems(data);
      // Auto-select the first (latest) if none is selected yet and items exist
      if (data.length > 0 && !activeKalkulacjaId) {
         onSelect(data[0].id, data[0].numer_kalkulacji);
      }
    } catch (err: unknown) {
      setError((err as Error).message || "Wystąpił błąd");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // listening for new calculations created by "Nowa kalkulacja"
    const handleNewCalc = (e: Event) => {
      if ((e as CustomEvent).detail?.vehicleId === vehicleId) {
         fetchHistory();
      }
    };
    window.addEventListener('kalkulacjaCreated', handleNewCalc);
    return () => window.removeEventListener('kalkulacjaCreated', handleNewCalc);
  }, [vehicleId, activeKalkulacjaId]); // fetchHistory was omitted by design, keeping simple as fetchHistory isn't memoized.

  if (loading && items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-6 bg-slate-50 border border-dashed border-slate-200 rounded-xl mt-4">
        <Loader2 className="w-5 h-5 animate-spin text-blue-500 mb-2" />
        <span className="text-xs font-medium text-slate-500">Ładowanie wariantów ofert...</span>
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="p-3 mt-4 bg-red-50 text-red-600 rounded-lg border border-red-100 text-xs">
        {error}
      </div>
    );
  }

  if (!loading && items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-dashed border-slate-200 rounded-xl text-center mt-4">
        <History className="w-6 h-6 text-slate-400 mb-2 opacity-50" />
        <h4 className="text-xs font-semibold text-slate-700">Brak wariantów ofert</h4>
        <p className="text-[10px] text-slate-500 mt-1 max-w-sm">
          Pojazd nie posiada jeszcze żadnych zapisanych kalkulacji. 
          Skonfiguruj parametry finansowe i utwórz nową kalkulację.
        </p>
      </div>
    );
  }

  const handleCloneClick = async (e: React.MouseEvent, kalkulacjaId: string) => {
    e.stopPropagation();
    if (onClone) {
        onClone(kalkulacjaId);
    }
  };

  return (
    <div className="flex flex-col gap-2 mt-4">
      <div className="flex items-center gap-2 mb-1 px-2">
        <History className="w-4 h-4 text-blue-500" />
        <h3 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">Warianty Ofert</h3>
        <span className="bg-slate-200 text-slate-600 text-[10px] font-bold px-1.5 py-0.5 rounded ml-1">
          {items.length}
        </span>
        {loading && <Loader2 className="w-3 h-3 animate-spin text-slate-400 ml-2" />}
      </div>

      <div className="overflow-x-auto border border-slate-200 rounded-lg shadow-sm">
        <table className="w-full text-left border-collapse text-sm bg-white">
          <thead>
            <tr className="bg-slate-50 text-slate-500 text-[10px] uppercase tracking-wider border-b border-slate-200">
              <th className="font-semibold py-2 px-3 lg:px-4">Numer / Data</th>
              <th className="font-semibold py-2 px-3 text-right">Rata Netto</th>
              <th className="font-semibold py-2 px-3 hidden md:table-cell w-[180px]">Parametry Auta</th>
              <th className="font-semibold py-2 px-3 hidden lg:table-cell w-[380px]">Konfiguracja (Włączone usługi)</th>
              <th className="font-semibold py-2 px-3 text-right">Akcje</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => {
              const isActive = activeKalkulacjaId === item.id;
              const date = new Date(item.created_at);
              const formattedDate = date.toLocaleDateString("pl-PL", { day: '2-digit', month: '2-digit', year: 'numeric' });
              const formattedTime = date.toLocaleTimeString("pl-PL", { hour: '2-digit', minute: '2-digit' });
              
              return (
                <tr 
                  key={item.id}
                  onClick={() => onSelect(item.id, item.numer_kalkulacji)}
                  className={cn(
                    "group transition-colors cursor-pointer hover:bg-slate-50/80",
                    isActive ? "bg-blue-50/50" : ""
                  )}
                >
                  {/* Number & Date */}
                  <td className="py-2.5 px-3 lg:px-4 align-middle relative">
                    {isActive && (
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500" />
                    )}
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                        <FileText className={cn("w-3 h-3", isActive ? "text-blue-500" : "text-slate-400")} />
                        {item.numer_kalkulacji}
                      </span>
                      <span className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                        <Clock className="w-2.5 h-2.5" /> {formattedDate} {formattedTime}
                      </span>
                    </div>
                  </td>
                  
                  {/* Price Netto */}
                  <td className="py-2.5 px-3 text-right align-middle">
                    {item.rata_netto != null ? (
                      <div className="flex flex-col items-end">
                        <span className="text-[13px] font-extrabold text-blue-700 tabular-nums">
                          {fmtPLN(item.rata_netto)} / mc
                        </span>
                        <span className="text-[10px] text-slate-400 mt-0.5" title="Wartość bazowa netto pojazdu">
                          Cena: {fmtPLN(item.cena_netto)}
                        </span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-end">
                        <span className="text-[11px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin"/> Przetwarzanie...
                        </span>
                        <span className="text-[10px] text-slate-400 mt-1" title="Wartość bazowa netto pojazdu">
                          Cena: {fmtPLN(item.cena_netto)}
                        </span>
                      </div>
                    )}
                  </td>

                  {/* Options & Discounts */}
                  <td className="py-2.5 px-3 hidden md:table-cell align-middle">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {item.options_count > 0 && (
                        <div className="flex items-center gap-1 text-[10px] font-medium text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                          <CarFront className="w-3 h-3" />
                          Opcje: {item.options_count}
                        </div>
                      )}
                      {item.discount_pct != null && (
                        <div className="flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">
                          Rabat -{item.discount_pct}%
                        </div>
                      )}
                    </div>
                    {item.matrix_count !== undefined && item.matrix_count > 0 && (
                      <div className="mt-1 flex items-center gap-1 text-[9px] text-slate-400 font-medium">
                        <Loader2 className="w-2.5 h-2.5 text-slate-300" />
                        Przeliczono {item.matrix_count} wariantów
                      </div>
                    )}
                  </td>

                  {/* Toggles Summary */}
                  <td className="py-2.5 px-3 hidden lg:table-cell align-middle">
                    <div className="flex flex-wrap items-center gap-2">
                       <ConfigBadge 
                          label="Serwis" 
                          enabled={!!item.toggles_summary?.include_service} 
                          icon={Wrench} 
                       />
                       <ConfigBadge 
                          label="Opony" 
                          enabled={!!item.toggles_summary?.include_tires} 
                          icon={Settings} 
                       />
                       <ConfigBadge 
                          label="Ubezpieczenie" 
                          enabled={!!item.toggles_summary?.include_insurance} 
                          icon={Shield} 
                       />
                       <ConfigBadge 
                          label="Auto zastępcze" 
                          enabled={!!item.toggles_summary?.include_replacement_car} 
                          icon={CarFront} 
                       />
                    </div>
                  </td>

                  {/* Actions */}
                  <td className="py-2.5 px-3 text-right align-middle whitespace-nowrap">
                    <div className="flex items-center justify-end gap-2">
                      {isActive ? (
                        <span className="text-[10px] font-bold text-blue-600 px-2 py-1 bg-blue-100/50 rounded pointer-events-none">
                          Aktywny
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-slate-400 group-hover:text-blue-500 px-2 py-1 transition-colors">
                          Wybierz <ChevronRight className="w-3 h-3 inline -mt-0.5" />
                        </span>
                      )}
                      
                      {onClone && (
                        <button
                          onClick={(e) => handleCloneClick(e, item.id)}
                          className={cn(
                            "flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded transition-colors",
                            "text-indigo-600 hover:bg-indigo-50 border border-transparent hover:border-indigo-100"
                          )}
                          title="Sklonuj ten wariant oferty"
                        >
                          <Copy className="w-3 h-3" />
                          Klonuj
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
