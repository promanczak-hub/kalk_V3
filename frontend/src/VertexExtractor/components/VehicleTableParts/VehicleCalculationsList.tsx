import { useState, useEffect, useMemo } from "react";
import { Loader2, History, Copy, Clock, CarFront, FileText, ChevronRight, Check, X, Shield, Wrench, Settings, Star } from "lucide-react";
import { cn } from "../../../lib/utils";
import { apiClient } from "../../../lib/apiClient";
import { fmtPLN } from "./calculations/calculations.utils";
import { API_BASE_URL } from "../../../config/env";

import { AgGridReact } from "ag-grid-react";
import { AllCommunityModule, type ColDef, type ICellRendererParams, ModuleRegistry, type RowClassRules } from "ag-grid-community";

ModuleRegistry.registerModules([AllCommunityModule]);

export interface TogglesSummary {
  z_oponami: boolean;
  express_pays_insurance: boolean;
  include_servicing: boolean;
  replacement_car: boolean;
  is_metalic?: boolean;
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
  is_selected?: boolean;
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
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] whitespace-nowrap font-medium",
      enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"
    )}
  >
    <Icon className="w-3 h-3" />
    <span className="hidden sm:inline">{label}</span>
    {enabled ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 opacity-50" />}
  </div>
);

/* --- Cell Renderers --- */

function NumberDateCellRenderer(params: ICellRendererParams<HistoricalCalculation> & { activeKalkulacjaId?: string | null }) {
  const item = params.data;
  if (!item) return null;
  const isActive = params.activeKalkulacjaId === item.id;
  const date = new Date(item.created_at);
  const formattedDate = date.toLocaleDateString("pl-PL", { day: '2-digit', month: '2-digit', year: 'numeric' });
  const formattedTime = date.toLocaleTimeString("pl-PL", { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="relative h-full flex flex-col justify-center">
      {isActive && (
        <div className="absolute -left-[17px] top-0 bottom-0 w-1 bg-blue-600 rounded-r-full" />
      )}
      <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
        <FileText className={cn("w-3 h-3", isActive ? "text-blue-500" : "text-slate-400")} />
        {item.numer_kalkulacji}
      </span>
      <span className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
        <Clock className="w-2.5 h-2.5" /> {formattedDate} {formattedTime}
      </span>
    </div>
  );
}

function PriceCellRenderer(params: ICellRendererParams<HistoricalCalculation>) {
  const item = params.data;
  if (!item) return null;

  return (
    <div className="flex flex-col items-end justify-center h-full">
      {item.rata_netto != null ? (
        <>
          <span className="text-[13px] font-extrabold text-blue-700 tabular-nums">
            {fmtPLN(item.rata_netto)} / mc
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5" title="Wartość bazowa netto pojazdu">
            Cena: {fmtPLN(item.cena_netto)}
          </span>
        </>
      ) : (
        <>
          <span className="text-[11px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin"/> Przetwarzanie...
          </span>
          <span className="text-[10px] text-slate-400 mt-1" title="Wartość bazowa netto pojazdu">
            Cena: {fmtPLN(item.cena_netto)}
          </span>
        </>
      )}
    </div>
  );
}

function ParamsCellRenderer(params: ICellRendererParams<HistoricalCalculation>) {
  const item = params.data;
  if (!item) return null;

  return (
    <div className="flex flex-col justify-center h-full gap-1">
      <div className="flex flex-wrap items-center gap-1.5">
        {item.options_count > 0 && (
          <div className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-700 bg-slate-100 px-2 py-0.5 rounded-full">
            <CarFront className="w-3 h-3" />
            Opcje: {item.options_count}
          </div>
        )}
        {item.discount_pct != null && (
          <div className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full">
            Rabat -{item.discount_pct}%
          </div>
        )}
      </div>
      {item.matrix_count !== undefined && item.matrix_count > 0 && (
        <div className="flex items-center gap-1 text-[9px] text-slate-400 font-medium mt-0.5">
          <Loader2 className="w-2.5 h-2.5 text-slate-300" />
          Przeliczono {item.matrix_count} wariantów
        </div>
      )}
    </div>
  );
}

function ConfigCellRenderer(params: ICellRendererParams<HistoricalCalculation>) {
  const item = params.data;
  if (!item) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 h-full content-center">
      <ConfigBadge
        label="Serwis"
        enabled={!!item.toggles_summary?.include_servicing}
        icon={Wrench}
      />
      <ConfigBadge
        label="Opony"
        enabled={!!item.toggles_summary?.z_oponami}
        icon={Settings}
      />
      <ConfigBadge
        label="Ubezpieczenie"
        enabled={!!item.toggles_summary?.express_pays_insurance}
        icon={Shield}
      />
      <ConfigBadge
        label="Auto zastępcze"
        enabled={!!item.toggles_summary?.replacement_car}
        icon={CarFront}
      />
    </div>
  );
}

function SelectedCellRenderer(
  params: ICellRendererParams<HistoricalCalculation> & {
    onToggleSelected?: (kalkulacjaId: string, makeSelected: boolean) => void;
    pendingId?: string | null;
  }
) {
  const item = params.data;
  if (!item) return null;
  const isSelected = !!item.is_selected;
  const isPending = params.pendingId === item.id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isPending) return;
    params.onToggleSelected?.(item.id, !isSelected);
  };

  return (
    <div className="flex items-center justify-center h-full">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        title={
          isSelected
            ? "Przypięta w wyszukiwarce — kliknij, by odpiąć"
            : "Przypnij w wyszukiwarce (możesz przypiąć kilka)"
        }
        className={cn(
          "p-1.5 rounded transition-colors",
          isSelected
            ? "text-amber-500 hover:text-amber-600 hover:bg-amber-50"
            : "text-slate-300 hover:text-amber-400 hover:bg-slate-50",
          isPending && "opacity-40 cursor-wait"
        )}
      >
        <Star className={cn("w-4 h-4", isSelected && "fill-current")} />
      </button>
    </div>
  );
}

function ActionsCellRenderer(params: ICellRendererParams<HistoricalCalculation> & { activeKalkulacjaId?: string | null, onClone?: (id: string) => void }) {
  const item = params.data;
  if (!item) return null;
  const isActive = params.activeKalkulacjaId === item.id;

  const handleCloneClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (params.onClone) {
      params.onClone(item.id);
    }
  };

  return (
    <div className="flex items-center justify-end gap-2 h-full">
      {isActive ? (
        <span className="text-[10px] font-semibold text-white px-2.5 py-1 bg-blue-600 rounded-full pointer-events-none shadow-sm">
          Aktywny
        </span>
      ) : (
        <span className="text-[10px] font-semibold text-slate-400 group-hover:text-blue-500 px-2 py-1 transition-colors">
          Wybierz <ChevronRight className="w-3 h-3 inline -mt-0.5" />
        </span>
      )}
      
      {params.onClone && (
        <button
          onClick={handleCloneClick}
          className={cn(
            "clone-btn",
            "inline-flex items-center gap-1 text-[10px] font-medium px-2.5 py-1 rounded-md transition-colors",
            "text-indigo-700 bg-indigo-50 hover:bg-indigo-100"
          )}
          title="Sklonuj ten wariant oferty"
        >
          <Copy className="w-3 h-3" />
          Klonuj
        </button>
      )}
    </div>
  );
}

/* --- Main Component --- */

export function VehicleCalculationsList({
  vehicleId,
  activeKalkulacjaId,
  onSelect,
  onClone
}: VehicleCalculationsListProps) {
  const [items, setItems] = useState<HistoricalCalculation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingSelectId, setPendingSelectId] = useState<string | null>(null);

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
  }, [vehicleId, activeKalkulacjaId]);

  const handleToggleSelected = async (kalkulacjaId: string, makeSelected: boolean) => {
    setPendingSelectId(kalkulacjaId);
    // Optimistically toggle just this row; backend stores the full pinned set.
    const nextItems = items.map((it) => ({
      ...it,
      is_selected: it.id === kalkulacjaId ? makeSelected : it.is_selected,
    }));
    setItems(nextItems);
    const nextIds = nextItems.filter((it) => it.is_selected).map((it) => it.id);
    try {
      const res = await apiClient.fetch(
        `${API_BASE_URL}/api/kalkulacje/vehicle/${vehicleId}/selected-calculation`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kalkulacja_ids: nextIds }),
        }
      );
      if (!res.ok) throw new Error("Nie udało się zapisać przypiętych kalkulacji");
      window.dispatchEvent(
        new CustomEvent("selectedKalkulacjaChanged", {
          detail: { vehicleId, kalkulacjaIds: nextIds },
        })
      );
    } catch (err) {
      setError((err as Error).message || "Błąd zapisu");
      fetchHistory();
    } finally {
      setPendingSelectId(null);
    }
  };

  /* --- AG Grid Setup --- */

  const columnDefs = useMemo<ColDef<HistoricalCalculation>[]>(() => [
    {
      headerName: "★",
      field: "is_selected",
      width: 56,
      cellRenderer: SelectedCellRenderer,
      cellRendererParams: { onToggleSelected: handleToggleSelected, pendingId: pendingSelectId },
      sortable: false,
      filter: false,
      headerTooltip: "Przypnij kalkulacje (każda przypięta = osobna karta w wyszukiwarce)",
    },
    {
      headerName: "Numer / Data",
      field: "numer_kalkulacji",
      flex: 1,
      minWidth: 150,
      cellRenderer: NumberDateCellRenderer,
      cellRendererParams: { activeKalkulacjaId }
    },
    {
      headerName: "Rata Netto",
      field: "rata_netto",
      width: 140,
      type: "rightAligned",
      cellRenderer: PriceCellRenderer,
    },
    {
      headerName: "Parametry Auta",
      field: "options_count",
      width: 160,
      cellRenderer: ParamsCellRenderer,
      // Hide on very small screens using AG Grid classes or minWidth strategy, 
      // but usually flex handles it or we can let it scroll
    },
    {
      headerName: "Konfiguracja (Włączone usługi)",
      width: 320,
      cellRenderer: ConfigCellRenderer,
      sortable: false,
      filter: false,
    },
    {
      headerName: "Akcje",
      width: 130,
      type: "rightAligned",
      cellRenderer: ActionsCellRenderer,
      cellRendererParams: { activeKalkulacjaId, onClone },
      sortable: false,
      filter: false,
    }
  ], [activeKalkulacjaId, onClone, pendingSelectId]);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    resizable: true,
    suppressMovable: true,
  }), []);

  const rowClassRules = useMemo<RowClassRules<HistoricalCalculation>>(() => ({
    "bg-blue-50": (params) => params.data?.id === activeKalkulacjaId,
    "cursor-pointer hover:bg-slate-50 transition-colors": () => true,
  }), [activeKalkulacjaId]);

  /* --- Renders --- */

  if (loading && items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-6 bg-slate-50 border border-dashed border-slate-300 rounded-lg mt-4">
        <Loader2 className="w-5 h-5 animate-spin text-blue-500 mb-2" />
        <span className="text-xs font-medium text-slate-500">Ładowanie wariantów ofert...</span>
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="p-3 mt-4 bg-red-50 text-red-700 rounded-md border border-red-200 text-xs">
        {error}
      </div>
    );
  }

  if (!loading && items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-dashed border-slate-300 rounded-lg text-center mt-4">
        <History className="w-6 h-6 text-slate-400 mb-2 opacity-50" />
        <h4 className="text-xs font-semibold text-slate-700">Brak wariantów ofert</h4>
        <p className="text-[10px] text-slate-500 mt-1 max-w-sm">
          Pojazd nie posiada jeszcze żadnych zapisanych kalkulacji. 
          Skonfiguruj parametry finansowe i utwórz nową kalkulację.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 mt-4">
      <div className="flex items-center gap-2 mb-1 px-2">
        <History className="w-4 h-4 text-blue-500" />
        <h3 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">Warianty Ofert</h3>
        <span className="bg-blue-100 text-blue-800 text-[10px] font-semibold px-2 py-0.5 rounded-full ml-1">
          {items.length}
        </span>
        {loading && <Loader2 className="w-3 h-3 animate-spin text-slate-400 ml-2" />}
      </div>

      <div className="ag-theme-quartz border border-slate-200 rounded-lg shadow-sm w-full overflow-hidden" style={{ height: Math.min(items.length, 5) * 60 + 45 }}>
        <AgGridReact<HistoricalCalculation>
          rowData={items}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          rowHeight={60}
          headerHeight={40}
          animateRows={true}
          rowClassRules={rowClassRules}
          getRowId={(params) => params.data.id}
          onRowClicked={(e) => {
            // Prevent selection if Klonuj was clicked
            if ((e.event?.target as HTMLElement)?.closest('.clone-btn')) return;
            if (e.data) {
                onSelect(e.data.id, e.data.numer_kalkulacji);
            }
          }}
          overlayNoRowsTemplate="<span class='text-slate-400 text-sm'>Brak wariantów ofert</span>"
        />
      </div>
    </div>
  );
}
