import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  Loader2,
  Trash2,
  RefreshCw,
  History,
  ExternalLink,
} from "lucide-react";
import { supabase } from "../lib/supabaseClient";
import type { FleetVehicleView } from "../VertexExtractor/types";
import { formatPrice } from "../VertexExtractor/components/VehicleTableParts/PriceDualFormat";
import { useNavigate } from "react-router-dom";

import { AgGridReact } from "ag-grid-react";
import { AllCommunityModule, type ColDef, type GridReadyEvent, type ICellRendererParams, ModuleRegistry } from "ag-grid-community";

ModuleRegistry.registerModules([AllCommunityModule]);

/* ─── Row shape for AG Grid ─── */
interface HistoryRow {
  id: string;
  saved_at: string;
  brand: string;
  model: string;
  version: string;
  catalog_price_net: number | null;
  final_price_net: number | null;
  discount_pct: number | null;
  wibor_pct: number | null;
  margin_pct: number | null;
  service_included: boolean;
  service_type: string;
  /* keep raw ref for delete */
  _raw: FleetVehicleView;
}

/* ─── Helpers ─── */
function calculateFinalPriceFromDiscount(base: number, pct: number): number {
  if (!base || !pct) return base;
  return Math.round(base * (1 - pct / 100) * 100) / 100;
}

function extractRow(v: FleetVehicleView): HistoryRow | null {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const synData = v.synthesis_data as any;
  const setup = synData?.calculator_setup;
  if (!setup) return null;

  const fin = setup.financial_params || {};
  const disc = setup.discount || {};
  const activePrice =
    disc.active_final_price ||
    calculateFinalPriceFromDiscount(
      setup.catalog_base_price_net,
      disc.active_discount_pct,
    ) ||
    null;

  return {
    id: v.id,
    saved_at: setup.saved_at || "",
    brand: v.brand || "",
    model: (v as Record<string, unknown>).model_family as string || v.model || "",
    version: (v as Record<string, unknown>).version_tag as string || "",
    catalog_price_net: setup.catalog_base_price_net || null,
    final_price_net: activePrice,
    discount_pct: disc.active_discount_pct || null,
    wibor_pct: fin.wibor_pct ?? null,
    margin_pct: fin.pricing_margin_pct ?? null,
    service_included: !!setup.toggles?.include_servicing,
    service_type: setup.service_cost_type === "nonASO" ? "Zależny" : "ASO",
    _raw: v,
  };
}

/* ─── Cell Renderers ─── */
function PriceCellRenderer(params: ICellRendererParams<HistoryRow>) {
  const val = params.value as number | null;
  if (!val) return <span className="text-slate-400">—</span>;
  return <span className="font-semibold tabular-nums">{formatPrice(val)}</span>;
}

function DateCellRenderer(params: ICellRendererParams<HistoryRow>) {
  const val = params.value as string;
  if (!val) return <span className="text-slate-400">—</span>;
  try {
    const d = new Date(val);
    return (
      <span className="text-xs tabular-nums">
        {d.toLocaleDateString("pl-PL")}
        <span className="ml-1 text-slate-400">
          {d.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </span>
    );
  } catch {
    return <span>{val}</span>;
  }
}

function ServiceCellRenderer(params: ICellRendererParams<HistoryRow>) {
  const row = params.data;
  if (!row) return null;
  return row.service_included ? (
    <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
      ✓ {row.service_type}
    </span>
  ) : (
    <span className="text-slate-400">✕ Brak</span>
  );
}

function PercentCellRenderer(params: ICellRendererParams<HistoryRow>) {
  const val = params.value as number | null;
  if (val === null || val === undefined) return <span className="text-slate-400">—</span>;
  return <span className="tabular-nums">{val}%</span>;
}

function VehicleCellRenderer(params: ICellRendererParams<HistoryRow>) {
  const row = params.data;
  if (!row) return null;
  return (
    <div className="flex flex-col justify-center leading-tight py-1">
      <span className="font-bold text-slate-800 text-[13px]">
        {row.brand} {row.model}
      </span>
      {row.version && (
        <span className="text-[11px] text-slate-500 truncate max-w-[260px]">
          {row.version}
        </span>
      )}
    </div>
  );
}

/* ─── Main Component ─── */
export function CalculationsHistoryPage() {
  const [vehicles, setVehicles] = useState<FleetVehicleView[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [quickFilter, setQuickFilter] = useState("");
  const gridRef = useRef<AgGridReact<HistoryRow>>(null);
  const navigate = useNavigate();

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const { data, error } = await supabase
        .from("fleet_management_view")
        .select("*")
        .not("synthesis_data->calculator_setup", "is", null)
        .order("created_at", { ascending: false });

      if (error) {
        console.error("Error fetching history:", error);
        setFetchError(
          `Nie udało się załadować historii kalkulacji: ${error.message}. Spróbuj ponownie.`,
        );
      } else {
        setVehicles((data as FleetVehicleView[]) || []);
      }
    } catch (err) {
      console.error(err);
      const msg = err instanceof Error ? err.message : String(err);
      setFetchError(`Błąd sieci: ${msg}. Sprawdź połączenie i odśwież stronę.`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  /* ── Row Data ── */
  const rowData = useMemo<HistoryRow[]>(() => {
    return vehicles.map(extractRow).filter(Boolean) as HistoryRow[];
  }, [vehicles]);

  /* ── Column Definitions ── */
  const columnDefs = useMemo<ColDef<HistoryRow>[]>(
    () => [
      {
        headerName: "Data zapisu",
        field: "saved_at",
        width: 150,
        sort: "desc",
        cellRenderer: DateCellRenderer,
        filter: "agDateColumnFilter",
      },
      {
        headerName: "Pojazd",
        field: "brand",
        flex: 2,
        minWidth: 220,
        cellRenderer: VehicleCellRenderer,
        filter: "agTextColumnFilter",
        filterValueGetter: (params) => {
          const d = params.data;
          if (!d) return "";
          return `${d.brand} ${d.model} ${d.version}`;
        },
      },
      {
        headerName: "Cena kat. netto",
        field: "catalog_price_net",
        width: 160,
        cellRenderer: PriceCellRenderer,
        filter: "agNumberColumnFilter",
        type: "rightAligned",
      },
      {
        headerName: "Rabat",
        field: "discount_pct",
        width: 90,
        cellRenderer: PercentCellRenderer,
        filter: "agNumberColumnFilter",
        type: "rightAligned",
      },
      {
        headerName: "Cena finalna netto",
        field: "final_price_net",
        width: 170,
        cellRenderer: PriceCellRenderer,
        filter: "agNumberColumnFilter",
        type: "rightAligned",
        cellClassRules: {
          "text-emerald-700": (params) => !!params.value,
        },
      },
      {
        headerName: "WIBOR",
        field: "wibor_pct",
        width: 90,
        cellRenderer: PercentCellRenderer,
        filter: "agNumberColumnFilter",
        type: "rightAligned",
      },
      {
        headerName: "Marża LTR",
        field: "margin_pct",
        width: 105,
        cellRenderer: PercentCellRenderer,
        filter: "agNumberColumnFilter",
        type: "rightAligned",
      },
      {
        headerName: "Serwis",
        field: "service_included",
        width: 120,
        cellRenderer: ServiceCellRenderer,
      },
      {
        headerName: "",
        field: "id",
        width: 120,
        sortable: false,
        filter: false,
        resizable: false,
        cellRenderer: ActionsCellRenderer,
        cellRendererParams: {
          onDelete: handleDeleteSetup,
          onOpen: handleOpenVertexExtractor,
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const defaultColDef = useMemo<ColDef<HistoryRow>>(
    () => ({
      sortable: true,
      resizable: true,
      filter: true,
      suppressMovable: false,
    }),
    [],
  );

  /* ── Actions ── */
  async function handleDeleteSetup(vehicleId: string) {
    if (
      !confirm(
        "Czy usunąć zapisaną konfigurację (setup) z tego pojazdu? Pojazd pozostanie w bazie.",
      )
    )
      return;
    try {
      const vehicle = vehicles.find((v) => v.id === vehicleId);
      if (!vehicle) return;

      const currentSynthesis =
        (vehicle.synthesis_data as Record<string, unknown>) || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      delete updatedJson.calculator_setup;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicleId);

      if (error) throw error;
      fetchHistory();
    } catch (err) {
      console.error(err);
      alert("Wystąpił błąd podczas usuwania kalkulacji.");
    }
  }

  async function handleOpenVertexExtractor(vehicleId: string) {
    // Verify the vehicle still exists in vehicle_synthesis before navigating.
    // Orphan vehicle_ids are a documented feature (memory `kalkulacja_vehicle_synthesis_link`)
    // — a kalkulacja can outlive its source vehicle. Without this guard,
    // /?highlight={vehicleId} loads VertexExtractor which then crashes on
    // missing data. Instead, show a clear message and offer to delete the
    // orphan setup record.
    try {
      const { data, error } = await supabase
        .from("vehicle_synthesis")
        .select("id")
        .eq("id", vehicleId)
        .maybeSingle();
      if (error) throw error;
      if (!data) {
        const proceed = window.confirm(
          "Pojazd źródłowy tej kalkulacji został usunięty.\n\n" +
          "Otworzyć Ekstraktor mimo to (możliwy błąd)?\n\n" +
          "OK = otwórz; Anuluj = wróć do listy.",
        );
        if (!proceed) return;
      }
    } catch (err) {
      console.error("Orphan check failed:", err);
      // Network blip — don't block navigation, but warn in console.
    }
    navigate(`/?highlight=${vehicleId}`);
  }

  /* ── Grid Callbacks ── */
  function onGridReady(_event: GridReadyEvent<HistoryRow>) {
    /* auto-size columns on initial load */
    _event.api.sizeColumnsToFit();
  }

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        <span>Ładowanie historii kalkulacji...</span>
      </div>
    );
  }

  /* ── Error state ── */
  if (fetchError) {
    return (
      <div className="max-w-2xl mx-auto mt-20 p-6 border border-red-200 bg-red-50 rounded-lg">
        <h2 className="text-lg font-semibold text-red-700 mb-2">
          Błąd ładowania historii
        </h2>
        <p className="text-sm text-red-600 mb-4 whitespace-pre-line">{fetchError}</p>
        <button
          type="button"
          onClick={() => fetchHistory()}
          className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded transition-colors"
        >
          Spróbuj ponownie
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto p-4 md:p-6 lg:p-8 h-[calc(100vh-80px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-600" />
            Historia Kalkulacji
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Zapisane parametry i wyniki dla przeliczonych pojazdów z systemu.
            <span className="ml-2 text-xs text-slate-400">
              ({rowData.length} rekordów)
            </span>
          </p>
        </div>
        <button
          onClick={fetchHistory}
          className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors border border-transparent hover:border-slate-200"
          title="Odśwież"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Quick Filter */}
      <div className="mb-4">
        <input
          type="text"
          value={quickFilter}
          onChange={(e) => setQuickFilter(e.target.value)}
          placeholder="Szukaj po marce, modelu, wersji..."
          className="w-full max-w-md pl-4 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none bg-white shadow-sm"
        />
      </div>

      {/* AG Grid */}
      <div className="ag-theme-quartz flex-1 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
        <AgGridReact<HistoryRow>
          ref={gridRef}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          quickFilterText={quickFilter}
          pagination={true}
          paginationPageSize={25}
          paginationPageSizeSelector={[10, 25, 50, 100]}
          rowHeight={52}
          headerHeight={40}
          animateRows={true}
          onGridReady={onGridReady}
          overlayNoRowsTemplate="<div class='flex flex-col items-center py-12'><span class='text-slate-400 text-sm'>Brak zapisanych kalkulacji</span></div>"
        />
      </div>
    </div>
  );
}

/* ─── Actions Cell Renderer (standalone for AG Grid) ─── */
function ActionsCellRenderer(
  params: ICellRendererParams<HistoryRow> & {
    onDelete: (id: string) => void;
    onOpen: (id: string) => void;
  },
) {
  const row = params.data;
  if (!row) return null;
  return (
    <div className="flex items-center gap-1 h-full">
      <button
        onClick={(e) => {
          e.stopPropagation();
          params.onOpen(row.id);
        }}
        className="p-1.5 text-indigo-500 hover:text-indigo-700 hover:bg-indigo-50 rounded-md transition-colors"
        title="Otwórz w edytorze"
      >
        <ExternalLink className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          params.onDelete(row.id);
        }}
        className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
        title="Usuń setup"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
