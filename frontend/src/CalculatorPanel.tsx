import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Chip,
} from "@mui/material";
import { Calculator, ChevronDown, ChevronUp, TrendingUp, Settings, RotateCcw, Loader2 } from "lucide-react";

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
  warnings?: {
    service_fallback_used?: boolean;
    replacement_car_missing?: boolean;
  };
}

interface CellOverrides {
  pricing_margin_pct: number;
  klasa_opony_string: string;
  liczba_kompletow_opon: number | null;
  z_oponami: boolean;
  manual_wr_correction: number;
  pakiet_serwisowy: number;
  inne_koszty_serwisowania_netto: number;
  service_cost_type: "ASO" | "nonASO";
  replacement_car_enabled: boolean;
  custom_months: number | null;        // null = use original
  custom_km_per_year: number | null;   // null = use original
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Payload = Record<string, any>;

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

// ─── Expert Panel Input Helpers ──────────────────────────────────────────────

function ExpertNumber({ label, value, onChange, step = 1, suffix, min }: {
  label: string; value: number; onChange: (v: number) => void; step?: number; suffix?: string; min?: number;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <label className="text-[11px] text-slate-500 font-medium shrink-0">{label}</label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          step={step}
          min={min}
          className="w-20 text-xs p-1 border border-slate-200 rounded text-right outline-none focus:ring-1 focus:ring-blue-500 tabular-nums bg-white"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        />
        {suffix && <span className="text-[10px] text-slate-400">{suffix}</span>}
      </div>
    </div>
  );
}

function ExpertToggle({ label, value, onChange }: {
  label: string; value: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <label className="text-[11px] text-slate-500 font-medium">{label}</label>
      <button
        onClick={() => onChange(!value)}
        className={`relative w-8 h-4.5 rounded-full transition-colors duration-200 ${value ? 'bg-blue-500' : 'bg-slate-300'}`}
      >
        <span className={`absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white shadow transition-transform duration-200 ${value ? 'left-4' : 'left-0.5'}`} />
      </button>
    </div>
  );
}

function ExpertSelect({ label, value, options, onChange }: {
  label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <label className="text-[11px] text-slate-500 font-medium shrink-0">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs p-1 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 bg-white"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ─── Expanded Cell Detail with Expert Mode ───────────────────────────────────

function CellDetail({
  cell,
  overrides,
  isModified,
  isRecalculating,
  onOverridesChange,
  onRecalculate,
  onReset,
}: {
  cell: MatrixCell;
  overrides: CellOverrides;
  isModified: boolean;
  isRecalculating: boolean;
  onOverridesChange: (o: CellOverrides) => void;
  onRecalculate: () => void;
  onReset: () => void;
}) {
  const bd = cell.breakdown;
  const [showExpert, setShowExpert] = useState(false);

  const update = (partial: Partial<CellOverrides>) => {
    onOverridesChange({ ...overrides, ...partial });
  };

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
          {isModified && (
            <Chip
              label="⚙️ Zmodyfikowana"
              size="small"
              color="info"
              variant="filled"
              sx={{ height: 20, fontSize: 10 }}
            />
          )}
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

      {/* Expert Mode Toggle */}
      <div className="mt-4 pt-3 border-t border-slate-200">
        <button
          onClick={() => setShowExpert(!showExpert)}
          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all ${
            showExpert
              ? "bg-blue-100 text-blue-700 border border-blue-200"
              : "bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200"
          }`}
        >
          <Settings className="w-3.5 h-3.5" />
          {showExpert ? "Zamknij tryb ekspercki" : "⚙️ Tryb ekspercki"}
        </button>
      </div>

      {/* Expert Panel */}
      {showExpert && (
        <div className="mt-3 p-3 bg-white rounded-lg border border-blue-100 animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2.5">
            {/* Column 1: Marża i Finanse */}
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Marża i Kontrakt</div>
              <ExpertNumber
                label="Marża sprzedaży"
                value={overrides.pricing_margin_pct}
                onChange={(v) => update({ pricing_margin_pct: v })}
                step={0.5}
                suffix="%"
                min={0}
              />
              <ExpertNumber
                label="Okres (mc)"
                value={overrides.custom_months ?? cell.months}
                onChange={(v) => update({ custom_months: v > 0 ? v : null })}
                step={6}
                suffix="mc"
                min={6}
              />
              <ExpertNumber
                label="Kilometry/rok"
                value={overrides.custom_km_per_year ?? cell.km_per_year}
                onChange={(v) => update({ custom_km_per_year: v > 0 ? v : null })}
                step={5000}
                suffix="km"
                min={5000}
              />
              <ExpertNumber
                label="Korekta WR"
                value={overrides.manual_wr_correction}
                onChange={(v) => update({ manual_wr_correction: v })}
                step={500}
                suffix="PLN"
              />
            </div>

            {/* Column 2: Serwis */}
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Serwis</div>
              <ExpertSelect
                label="Typ serwisu"
                value={overrides.service_cost_type}
                options={[
                  { value: "ASO", label: "ASO" },
                  { value: "nonASO", label: "Non-ASO" },
                ]}
                onChange={(v) => update({ service_cost_type: v as "ASO" | "nonASO" })}
              />
              <ExpertNumber
                label="Pakiet serwisowy"
                value={overrides.pakiet_serwisowy}
                onChange={(v) => update({ pakiet_serwisowy: v })}
                step={100}
                suffix="PLN"
                min={0}
              />
              <ExpertNumber
                label="Inne koszty mc"
                value={overrides.inne_koszty_serwisowania_netto}
                onChange={(v) => update({ inne_koszty_serwisowania_netto: v })}
                step={10}
                suffix="PLN"
                min={0}
              />
            </div>

            {/* Column 3: Opony i Toggles */}
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Opony i Inne</div>
              <ExpertToggle
                label="Opony"
                value={overrides.z_oponami}
                onChange={(v) => update({ z_oponami: v })}
              />
              <ExpertSelect
                label="Klasa opon"
                value={overrides.klasa_opony_string}
                options={[
                  { value: "Budget", label: "Budget" },
                  { value: "Medium", label: "Medium" },
                  { value: "Premium", label: "Premium" },
                ]}
                onChange={(v) => update({ klasa_opony_string: v })}
              />
              <ExpertToggle
                label="Auto zastępcze"
                value={overrides.replacement_car_enabled}
                onChange={(v) => update({ replacement_car_enabled: v })}
              />
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-blue-50">
            <div className="flex items-center gap-2">
              <button
                onClick={onRecalculate}
                disabled={isRecalculating}
                className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRecalculating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <TrendingUp className="w-3.5 h-3.5" />
                )}
                {isRecalculating ? "Przeliczam..." : "Przelicz tę komórkę"}
              </button>
              {isModified && (
                <button
                  onClick={onReset}
                  className="flex items-center gap-1 text-xs font-medium px-3 py-2 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all border border-slate-200"
                >
                  <RotateCcw className="w-3 h-3" />
                  Resetuj
                </button>
              )}
            </div>
            <div className="text-right">
              <div className="text-[10px] text-slate-400 uppercase">Rata LTR netto</div>
              <div className="text-lg font-bold text-blue-700 tabular-nums">{fmtPLN(cell.price_net)} PLN</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function CalculatorPanel() {
  const [cells, setCells] = useState<MatrixCell[]>([]);
  const [originalCells, setOriginalCells] = useState<MatrixCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCell, setExpandedCell] = useState<number | null>(null);
  const [cellOverrides, setCellOverrides] = useState<Record<number, CellOverrides>>({});
  const [modifiedCells, setModifiedCells] = useState<Set<number>>(new Set());
  const [recalculating, setRecalculating] = useState<number | null>(null);

  // Store the base payload for per-cell recalculation
  const basePayloadRef = useRef<Payload | null>(null);
  const kmPerMonthRef = useRef<number>(0);

  // Read kalkulacja ID from URL
  const urlParams = new URLSearchParams(window.location.search);
  const kalkulacjaId = urlParams.get("id");
  const kalkulacjaNumer = urlParams.get("kalkulacja") || "Brak numeru";

  // Build default overrides from base payload
  const buildDefaultOverrides = (payload: Payload): CellOverrides => ({
    pricing_margin_pct: payload.pricing_margin_pct ?? 15.0,
    klasa_opony_string: payload.klasa_opony_string || "Medium",
    liczba_kompletow_opon: payload.liczba_kompletow_opon ?? null,
    z_oponami: payload.z_oponami !== false,
    manual_wr_correction: payload.manual_wr_correction || 0,
    pakiet_serwisowy: payload.pakiet_serwisowy || 0,
    inne_koszty_serwisowania_netto: payload.inne_koszty_serwisowania_netto || 0,
    service_cost_type: payload.service_cost_type || "ASO",
    replacement_car_enabled: payload.replacement_car_enabled !== false,
    custom_months: null,
    custom_km_per_year: null,
  });

  // Get or initialize overrides for a cell
  const getOverrides = (months: number): CellOverrides => {
    if (cellOverrides[months]) return cellOverrides[months];
    if (basePayloadRef.current) return buildDefaultOverrides(basePayloadRef.current);
    return {
      pricing_margin_pct: 15.0,
      klasa_opony_string: "Medium",
      liczba_kompletow_opon: null,
      z_oponami: true,
      manual_wr_correction: 0,
      pakiet_serwisowy: 0,
      inne_koszty_serwisowania_netto: 0,
      service_cost_type: "ASO",
      replacement_car_enabled: true,
      custom_months: null,
      custom_km_per_year: null,
    };
  };

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

      const okresBazowy = mappedAi.usage_months || 48;
      const przebiegBazowy = mappedAi.total_km || 140000;
      kmPerMonthRef.current = przebiegBazowy / okresBazowy;

      // 2. Build CalculatorInput payload from stan_json
      const payload: Payload = {
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
        okres_bazowy: okresBazowy,
        przebieg_bazowy: przebiegBazowy,
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
        pricing_margin_pct: financialParams.pricing_margin_pct ?? 15.0,
        manual_wr_correction: 0,
        pakiet_serwisowy: 0,
        inne_koszty_serwisowania_netto: 0,
        settings: { settings_version_id: null, overrides: null },
      };

      // Store base payload for per-cell recalculation
      basePayloadRef.current = payload;

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
      const newCells = matrixData.cells || [];
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});
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

  // ─── Per-cell recalculation ────────────────────────────────────────────────

  const recalculateSingleCell = useCallback(async (months: number) => {
    if (!basePayloadRef.current) return;
    const ov = cellOverrides[months];
    if (!ov) return;

    setRecalculating(months);
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

      // Build modified payload: apply expert overrides.
      // If user specified custom months/km, use those; otherwise keep original cell's.
      const effectiveMonths = ov.custom_months ?? months;
      const effectiveKmYear = ov.custom_km_per_year;
      let targetKm: number;
      if (effectiveKmYear != null) {
        targetKm = Math.round((effectiveKmYear / 12) * effectiveMonths);
      } else {
        targetKm = Math.round(kmPerMonthRef.current * effectiveMonths);
      }

      const modifiedPayload: Payload = {
        ...basePayloadRef.current,
        okres_bazowy: effectiveMonths,
        przebieg_bazowy: targetKm,
        // Apply expert overrides
        pricing_margin_pct: ov.pricing_margin_pct,
        klasa_opony_string: ov.klasa_opony_string,
        liczba_kompletow_opon: ov.liczba_kompletow_opon,
        z_oponami: ov.z_oponami,
        manual_wr_correction: ov.manual_wr_correction,
        pakiet_serwisowy: ov.pakiet_serwisowy,
        inne_koszty_serwisowania_netto: ov.inne_koszty_serwisowania_netto,
        service_cost_type: ov.service_cost_type,
        replacement_car_enabled: ov.replacement_car_enabled,
      };

      const resp = await fetch(`${baseUrl}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd przeliczania komórki");
      const data = await resp.json();
      const newCells: MatrixCell[] = data.cells || [];

      // Find the cell matching our effective months
      const foundMonths = ov.custom_months ?? months;
      const targetCell = newCells.find(c => c.months === foundMonths);
      if (targetCell) {
        setCells(prev => prev.map(c => c.months === months ? targetCell : c));
        setModifiedCells(prev => new Set([...prev, months]));
      }
    } catch (err) {
      console.error("Recalculation error:", err);
    } finally {
      setRecalculating(null);
    }
  }, [cellOverrides]);

  const resetCell = (months: number) => {
    const original = originalCells.find(c => c.months === months);
    if (original) {
      setCells(prev => prev.map(c => c.months === months ? original : c));
    }
    setCellOverrides(prev => {
      const next = { ...prev };
      delete next[months];
      return next;
    });
    setModifiedCells(prev => {
      const next = new Set(prev);
      next.delete(months);
      return next;
    });
  };

  const handleOverridesChange = (months: number, overrides: CellOverrides) => {
    setCellOverrides(prev => ({ ...prev, [months]: overrides }));
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
            {modifiedCells.size > 0 && (
              <span className="text-[10px] text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded">
                {modifiedCells.size} zmodyfikowana(e)
              </span>
            )}
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

            {/* Data quality warnings */}
            {cells.some(c => c.warnings?.service_fallback_used) && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 mb-3 flex items-center gap-2">
                <span className="text-amber-600 text-sm">⚠️</span>
                <span className="text-xs text-amber-800 font-medium">
                  Brak stawek serwisowych SAMAR dla tego pojazdu — koszt serwisu = 0 PLN. Uzupełnij dane w Control Center.
                </span>
              </div>
            )}
            {cells.some(c => c.warnings?.replacement_car_missing) && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 mb-3 flex items-center gap-2">
                <span className="text-amber-600 text-sm">⚠️</span>
                <span className="text-xs text-amber-800 font-medium">
                  Brak danych auta zastępczego dla tej klasy SAMAR — koszt = 0 PLN. Sprawdź mapowanie klasy WR → SAMAR.
                </span>
              </div>
            )}

            {/* Matrix Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {cells.map((cell) => {
                const isExpanded = expandedCell === cell.months;
                const isMod = modifiedCells.has(cell.months);

                return (
                  <div key={cell.months} className={isExpanded ? "sm:col-span-2 lg:col-span-3 xl:col-span-4" : ""}>
                    {/* Matrix Cell Card */}
                    <button
                      onClick={() => setExpandedCell(isExpanded ? null : cell.months)}
                      className={`w-full text-left p-3 rounded-lg border transition-all cursor-pointer hover:shadow-md ${
                        isExpanded
                          ? "bg-blue-50 border-blue-300 shadow-md"
                          : isMod
                            ? "bg-blue-50/50 border-blue-200 hover:border-blue-400 ring-1 ring-blue-100"
                            : cell.status === "OK"
                              ? "bg-white border-slate-200 hover:border-blue-300"
                              : "bg-amber-50/50 border-amber-200 hover:border-amber-400"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <div className="text-xs font-bold text-slate-400 uppercase">
                              {cell.months} miesięcy
                            </div>
                            {isMod && <Settings className="w-3 h-3 text-blue-500" />}
                          </div>
                          <div className="text-xs text-slate-400">
                            {(cell.total_km / 1000).toFixed(0)}k km ({cell.km_per_year.toLocaleString("pl-PL")} km/rok)
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-right">
                            <div className="text-sm font-bold text-blue-700 tabular-nums">
                              {fmtPLN(cell.price_net)}
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

                    {/* Expanded Detail with Expert Mode */}
                    {isExpanded && (
                      <CellDetail
                        cell={cell}
                        overrides={getOverrides(cell.months)}
                        isModified={isMod}
                        isRecalculating={recalculating === cell.months}
                        onOverridesChange={(o) => handleOverridesChange(cell.months, o)}
                        onRecalculate={() => recalculateSingleCell(cell.months)}
                        onReset={() => resetCell(cell.months)}
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
