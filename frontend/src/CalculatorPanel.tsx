import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Chip,
} from "@mui/material";
import { Calculator, ChevronDown, ChevronUp, TrendingUp, DollarSign } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface CostComponent {
  base: number;
  margin: number;
  price: number;
}

interface CellBreakdown {
  finance: CostComponent & {
    monthly_pmt: number;
    total_interest: number;
    total_capital_repayment: number;
    initial_deposit_net: number;
  };
  technical: {
    service: CostComponent;
    tires: CostComponent;
    insurance: CostComponent;
    replacement_car: CostComponent;
    additional_costs: CostComponent;
  };
}

interface MatrixCell {
  months: number;
  km_per_year: number;
  total_km: number;
  base_cost_net: number;
  price_net: number;
  rv_samar_net: number;
  rv_lo_net: number;
  utrata_wartosci_bez_czynszu_net: number;
  breakdown: CellBreakdown;
  status: string;
}

// ─── Helper ──────────────────────────────────────────────────────────────────

function fmtPLN(val: number): string {
  return val.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── CostRow ─────────────────────────────────────────────────────────────────

function CostRow({ label, component }: { label: string; component: CostComponent }) {
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="py-1.5 text-xs text-slate-600 font-medium">{label}</td>
      <td className="py-1.5 text-xs text-right text-slate-700 tabular-nums">{fmtPLN(component.base)}</td>
      <td className="py-1.5 text-xs text-right text-slate-500 tabular-nums">{fmtPLN(component.margin)}</td>
      <td className="py-1.5 text-xs text-right font-semibold text-slate-800 tabular-nums">{fmtPLN(component.price)}</td>
    </tr>
  );
}

// ─── Expanded Cell Detail ────────────────────────────────────────────────────

function CellDetail({
  cell,
  marginAdj,
  onMarginChange,
}: {
  cell: MatrixCell;
  marginAdj: number;
  onMarginChange: (val: number) => void;
}) {
  const bd = cell.breakdown;
  const adjustedTotal = cell.price_net + marginAdj;

  return (
    <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 mt-2 animate-in fade-in slide-in-from-top-2 duration-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-500 uppercase">
            {cell.months} mc / {(cell.total_km / 1000).toFixed(0)}k km
          </span>
          <Chip
            label={cell.status === "OK" ? "OK" : "⚠ Wysoki przebieg"}
            size="small"
            color={cell.status === "OK" ? "success" : "warning"}
            variant="outlined"
            sx={{ height: 20, fontSize: 10 }}
          />
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-400 uppercase">WR SAMAR netto</div>
          <div className="text-xs font-bold text-emerald-700">{fmtPLN(cell.rv_samar_net)} PLN</div>
        </div>
      </div>

      {/* Cost breakdown table */}
      <table className="w-full">
        <thead>
          <tr className="border-b-2 border-slate-200">
            <th className="pb-1 text-xs text-left font-bold text-slate-400 uppercase w-[40%]">Składnik</th>
            <th className="pb-1 text-xs text-right font-bold text-slate-400 uppercase w-[20%]">Baza netto</th>
            <th className="pb-1 text-xs text-right font-bold text-slate-400 uppercase w-[20%]">Marża</th>
            <th className="pb-1 text-xs text-right font-bold text-slate-400 uppercase w-[20%]">Cena netto</th>
          </tr>
        </thead>
        <tbody>
          <CostRow label="Finansowanie (PMT)" component={bd.finance} />
          <CostRow label="Serwis" component={bd.technical.service} />
          <CostRow label="Opony" component={bd.technical.tires} />
          <CostRow label="Ubezpieczenie" component={bd.technical.insurance} />
          <CostRow label="Samochód zastępczy" component={bd.technical.replacement_car} />
          <CostRow label="Inne koszty" component={bd.technical.additional_costs} />
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-slate-300">
            <td className="pt-2 text-xs font-bold text-slate-800">RAZEM (rata LTR)</td>
            <td className="pt-2 text-xs text-right font-bold text-slate-700 tabular-nums">{fmtPLN(cell.base_cost_net)}</td>
            <td></td>
            <td className="pt-2 text-sm text-right font-bold text-blue-700 tabular-nums">{fmtPLN(cell.price_net)}</td>
          </tr>
        </tfoot>
      </table>

      {/* Margin adjustment */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-200">
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-slate-500 uppercase">Dodatkowa marża (PLN/mc):</label>
          <input
            type="number"
            step="10"
            className="w-24 text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 tabular-nums"
            value={marginAdj}
            onChange={(e) => onMarginChange(parseFloat(e.target.value) || 0)}
          />
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-slate-400">Cena końcowa netto</div>
            <div className="text-base font-bold text-blue-700 tabular-nums">{fmtPLN(adjustedTotal)} PLN</div>
          </div>
          <button className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-all shadow-sm">
            <DollarSign className="w-3.5 h-3.5 mr-1.5" />
            Dostosuj cenę
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function CalculatorPanel() {
  const [cells, setCells] = useState<MatrixCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCell, setExpandedCell] = useState<number | null>(null);
  const [marginAdjustments, setMarginAdjustments] = useState<Record<number, number>>({});

  // Read kalkulacja ID from URL
  const urlParams = new URLSearchParams(window.location.search);
  const kalkulacjaId = urlParams.get("id");
  const kalkulacjaNumer = urlParams.get("kalkulacja") || "Brak numeru";

  // Fetch matrix
  const fetchMatrix = useCallback(async () => {
    if (!kalkulacjaId) {
      setError("Brak ID kalkulacji. Wróć do Vertex Extractor i kliknij 'Zrób kalkulację'.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

      // 1. Fetch kalkulacja data (stan_json) from backend
      const kalkResp = await fetch(`${baseUrl}/api/kalkulacje/${kalkulacjaId}`);
      if (!kalkResp.ok) throw new Error(`Nie znaleziono kalkulacji ${kalkulacjaId}`);
      const kalkData = await kalkResp.json();
      const stanJson = kalkData.stan_json || {};
      const cardSummary = stanJson.card_summary || {};
      const financialParams = stanJson.financial_params || {};
      const toggles = stanJson.toggles || {};
      const mappedAi = stanJson.mapped_ai_data || {};
      const discount = stanJson.discount || {};

      // 2. Build CalculatorInput payload from stan_json
      const payload = {
        calculation_id: kalkulacjaId,
        vehicle_id: kalkData.vehicle_id || cardSummary.model || "unknown",
        base_price_net: parseFloat(cardSummary.base_price || cardSummary.total_price || "0"),
        discount_pct: discount.active_discount_pct || 0,
        factory_options: (stanJson.factory_options || []).map((o: { name: string; price_net: number; include_in_wr?: boolean }) => ({
          name: o.name || "Opcja",
          price_net: o.price_net || 0,
          include_in_wr: false,
        })),
        service_options: (stanJson.service_options || []).map((o: { name: string; price_net: number; include_in_wr?: boolean }) => ({
          name: o.name || "Usługa",
          price_net: o.price_net || 0,
          include_in_wr: o.include_in_wr || false,
        })),
        okres_bazowy: mappedAi.usage_months || 48,
        przebieg_bazowy: mappedAi.total_km || 140000,
        wibor_pct: financialParams.wibor_pct || 5.0,
        margin_pct: financialParams.margin_pct || 2.0,
        depreciation_pct: financialParams.depreciation_pct || null,
        initial_deposit_pct: financialParams.initial_deposit_pct || 0,
        replacement_car_enabled: toggles.replacement_car !== false,
        add_gsm_subscription: toggles.gps_required !== false,
        add_hook_installation: toggles.hook_installation === true,
        z_oponami: toggles.z_oponami !== false,
        klasa_opony_string: stanJson.tire_params?.tire_class || "Medium",
        srednica_felgi: stanJson.tire_params?.rim_diameter || null,
        liczba_kompletow_opon: stanJson.tire_params?.tire_count_mode === "auto" ? null : parseFloat(stanJson.tire_params?.tire_count_mode) || null,
        korekta_kosztu_opon: stanJson.tire_params?.tire_cost_correction_enabled !== false,
        koszt_opon_korekta: stanJson.tire_params?.tire_cost_correction || 0,
        service_cost_type: stanJson.service_cost_type || "ASO",
        vehicle_vintage: stanJson.vehicle_vintage || "current",
        is_metalic: stanJson.is_metalic === true,
        settings: { settings_version_id: null, overrides: null },
      };

      // 3. Call calculate-matrix
      const matrixResp = await fetch(`${baseUrl}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!matrixResp.ok) {
        const errBody = await matrixResp.text();
        throw new Error(`Błąd kalkulacji: ${errBody}`);
      }
      const matrixData = await matrixResp.json();
      setCells(matrixData.cells || []);
    } catch (err) {
      console.error("Matrix fetch error:", err);
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setLoading(false);
    }
  }, [kalkulacjaId]);

  useEffect(() => {
    fetchMatrix();
  }, [fetchMatrix]);

  const handleMarginChange = (months: number, val: number) => {
    setMarginAdjustments((prev) => ({ ...prev, [months]: val }));
  };

  // ─── Render ──────────────────────────────────────────────────────────────

  if (!kalkulacjaId) {
    return (
      <Box sx={{ p: 6, textAlign: "center" }}>
        <Typography variant="h6" color="text.secondary">
          Wybierz kalkulację z listy lub utwórz nową w Vertex Extractor.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ pb: 5, backgroundColor: "#fcfcfc", minHeight: "100vh" }}>
      {/* Top Banner */}
      <Box sx={{ p: 2, borderBottom: "1px solid #e2e8f0", mb: 2, bgcolor: "#fff" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calculator className="w-6 h-6 text-blue-700" />
            <div>
              <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2 }}>
                Kalkulacja: {kalkulacjaNumer}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                ID: {kalkulacjaId}
              </Typography>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchMatrix}
              className="flex items-center text-xs font-semibold px-3 py-1.5 rounded bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 transition-colors"
            >
              <TrendingUp className="w-3.5 h-3.5 mr-1.5" />
              Przelicz ponownie
            </button>
          </div>
        </div>
      </Box>

      {/* Main content */}
      <Box sx={{ px: 2, maxWidth: "1400px", margin: "0 auto" }}>
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <CircularProgress size={48} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Obliczanie matrycy LTR...
            </Typography>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <Typography variant="body2" color="error" sx={{ fontWeight: "bold" }}>
              Błąd: {error}
            </Typography>
            <button
              onClick={fetchMatrix}
              className="mt-2 text-xs font-semibold px-4 py-1.5 rounded bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
            >
              Spróbuj ponownie
            </button>
          </div>
        )}

        {!loading && !error && cells.length > 0 && (
          <div>
            <h3 className="flex items-center text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
              <Calculator className="w-4 h-4 mr-2" />
              Matryca rat LTR ({cells.length} wariantów)
            </h3>

            {/* Matrix Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {cells.map((cell) => {
                const isExpanded = expandedCell === cell.months;
                const adj = marginAdjustments[cell.months] || 0;
                const displayPrice = cell.price_net + adj;

                return (
                  <div key={cell.months} className={isExpanded ? "sm:col-span-2 lg:col-span-3 xl:col-span-4" : ""}>
                    {/* Matrix Cell Card */}
                    <button
                      onClick={() => setExpandedCell(isExpanded ? null : cell.months)}
                      className={`w-full text-left p-3 rounded-lg border transition-all cursor-pointer hover:shadow-md ${
                        isExpanded
                          ? "bg-blue-50 border-blue-300 shadow-md"
                          : cell.status === "OK"
                            ? "bg-white border-slate-200 hover:border-blue-300"
                            : "bg-amber-50/50 border-amber-200 hover:border-amber-400"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-xs font-bold text-slate-400 uppercase">
                            {cell.months} miesięcy
                          </div>
                          <div className="text-xs text-slate-400">
                            {(cell.total_km / 1000).toFixed(0)}k km ({cell.km_per_year.toLocaleString("pl-PL")} km/rok)
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-right">
                            <div className="text-sm font-bold text-blue-700 tabular-nums">
                              {fmtPLN(displayPrice)}
                            </div>
                            <div className="text-[9px] text-slate-400">PLN netto/mc</div>
                          </div>
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      </div>
                    </button>

                    {/* Expanded Detail */}
                    {isExpanded && (
                      <CellDetail
                        cell={cell}
                        marginAdj={adj}
                        onMarginChange={(val) => handleMarginChange(cell.months, val)}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {!loading && !error && cells.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <Calculator className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <Typography variant="body1">Brak wyników matrycy</Typography>
            <Typography variant="body2" color="text.secondary">
              Sprawdź dane wejściowe na karcie pojazdu w Vertex Extractor.
            </Typography>
          </div>
        )}
      </Box>
    </Box>
  );
}
