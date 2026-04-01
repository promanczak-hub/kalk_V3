import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  Trash2,
  RefreshCw,
  Search,
  History,
  ArrowRight,
} from "lucide-react";
import { supabase } from "../lib/supabaseClient";
import type { FleetVehicleView } from "../VertexExtractor/types";
import { formatPrice } from "../VertexExtractor/components/VehicleTableParts/PriceDualFormat";
import { useNavigate } from "react-router-dom";

export function CalculationsHistoryPage() {
  const [vehicles, setVehicles] = useState<FleetVehicleView[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch vehicles where calculator_setup is strictly NOT NULL
      // Using not.is.null syntax for jsonb path
      const { data, error } = await supabase
        .from("fleet_management_view")
        .select("*")
        .not("synthesis_data->calculator_setup", "is", null)
        .order("created_at", { ascending: false });

      if (error) {
        console.error("Error fetching history:", error);
      } else {
        setVehicles((data as FleetVehicleView[]) || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleDeleteSetup = async (vehicleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Czy usunąć zapisaną konfigurację (setup) z tego pojazdu? Pojazd pozostanie w bazie.")) return;
    try {
      const vehicle = vehicles.find((v) => v.id === vehicleId);
      if (!vehicle) return;

      const currentSynthesis = (vehicle.synthesis_data as Record<string, unknown>) || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      // Remove calculator setup
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
  };

  const handleOpenVertexExtractor = (vehicleId: string) => {
    navigate(`/?highlight=${vehicleId}`);
  };

  const filtered = vehicles.filter((v) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const modelStr = `${v.brand || ""} ${v.model_family || ""} ${v.model_name || ""} ${v.version_tag || ""}`.toLowerCase();
    return modelStr.includes(q);
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        <span>Ładowanie historii kalkulacji...</span>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto p-4 md:p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-600" />
            Historia Kalkulacji
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Zapisane parametry i wyniki ("fingerprint") dla przeliczonych pojazdów z systemu.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchHistory}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors border border-transparent hover:border-slate-200"
            title="Odśwież"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Szukaj po marce, modelu lub opisie..."
          className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none bg-white shadow-sm"
        />
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm">
          <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mx-auto mb-4 border border-slate-100">
            <History className="w-7 h-7 text-slate-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-600 mb-1">
            {vehicles.length === 0 ? "Brak zapisanych kalkulacji" : "Brak wyników wyszukiwania"}
          </h3>
          <p className="text-xs text-slate-400">
            {vehicles.length === 0
              ? 'Skonfiguruj pojazd w panelu Extractor i zapisz wynik przyciskiem z ikoną dyskietki.'
              : "Spróbuj zmienić filtry lub wyszukiwaną frazę."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((v) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const synData = v.synthesis_data as any;
            const setup = synData?.calculator_setup;
            if (!setup) return null;

            const savedAt = setup.saved_at ? new Date(setup.saved_at).toLocaleDateString("pl-PL", {
              hour: '2-digit', minute: '2-digit'
            }) : "Nieznana data";

            const fin = setup.financial_params || {};
            const disc = setup.discount || {};
            const activePrice = disc.active_final_price || calculateFinalPriceFromDiscount(setup.catalog_base_price_net, disc.active_discount_pct) || v.base_price;

            return (
              <div
                key={v.id}
                onClick={() => handleOpenVertexExtractor(v.id)}
                className="group relative bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer flex flex-col"
              >
                {/* Status Bar */}
                <div className="h-1 w-full bg-gradient-to-r from-indigo-500 to-blue-500" />

                <div className="p-4 sm:p-5 flex flex-col flex-1">
                  {/* Top line */}
                  <div className="flex justify-between items-start mb-2">
                    <div className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider">
                      {savedAt}
                    </div>
                    
                    <button
                      onClick={(e) => handleDeleteSetup(v.id, e)}
                      className="text-slate-300 hover:text-red-500 hover:bg-red-50 p-1.5 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                      title="Usuń zachowany setup"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Vehicle Label */}
                  <h3 className="font-bold text-slate-800 text-base leading-tight mb-1 line-clamp-1">
                    {v.brand} {v.model_family}
                  </h3>
                  <p className="text-xs text-slate-500 font-medium mb-3 line-clamp-1">
                    {v.version_tag ? v.version_tag : v.model_name}
                  </p>

                  <div className="h-px w-full bg-slate-100 my-2" />

                  {/* Key Stats Grid */}
                  <div className="grid grid-cols-2 gap-y-3 gap-x-2 my-2 mt-3">
                    <div>
                      <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Cena bazy (kat.)</span>
                      <span className="text-xs font-semibold text-slate-700">
                        {setup.catalog_base_price_net ? formatPrice(setup.catalog_base_price_net) + " Netto" : "-"}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Zapisana Cena Poj.</span>
                      <span className="text-xs font-bold text-emerald-700">
                        {activePrice ? formatPrice(activePrice) + " Netto" : "-"}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">WIBOR / Marża LTR</span>
                      <span className="text-xs font-medium text-slate-600">
                         {fin.wibor_pct || 0}% / {fin.pricing_margin_pct || 0}%
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Pakiet Serwisu</span>
                      <span className="text-xs font-medium text-slate-600">
                        {setup.toggles?.include_servicing ? "✓ Wliczony" : "✕ Brak"} {setup.service_cost_type === 'nonASO' ? '(Zależny)' : '(ASO)'}
                      </span>
                    </div>
                  </div>

                  {/* Spacer to push button down */}
                  <div className="flex-1" />

                  {/* Bottom Action */}
                  <div className="mt-4 flex items-center justify-between text-indigo-600 font-medium text-xs group-hover:text-indigo-700">
                    <span>Otwórz w edytorze</span>
                    <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function calculateFinalPriceFromDiscount(base: number, pct: number) {
  if (!base || !pct) return base;
  return Math.round(base * (1 - pct / 100) * 100) / 100;
}
