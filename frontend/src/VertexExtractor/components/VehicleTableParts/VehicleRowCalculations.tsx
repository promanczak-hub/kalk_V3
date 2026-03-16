import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Box,
  Typography,
  Chip,
} from "@mui/material";
import { Calculator, ChevronDown, ChevronUp, TrendingUp, Settings, RotateCcw, Loader2, FileCode2, X } from "lucide-react";
import { API_BASE_URL } from "../../../config/env";
import { MatrixFilterToolbar, type MatrixFilters, type MileageMode } from "../../../CalculatorPanel/MatrixFilterToolbar";
import { ReversePriceLookup } from "../../../CalculatorPanel/ReversePriceLookup";
import { MatrixHeatmapView, MatrixViewToggle } from "../../../CalculatorPanel/MatrixHeatmapView";

// ─── Types ───────────────────────────────────────────────────────────────────

import type { MiniMatrixCell } from "./decision-center/decision-center.types";

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

type NormalizedOption = {
  name: string;
  price_net: number;
  price_gross: number;
  no_discount: boolean;
  include_in_wr: boolean;
};

// ─── Helper ──────────────────────────────────────────────────────────────────

function fmtPLN(val: number): string {
  return val.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function parsePriceToNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return 0;

  const normalized = value
    .replace(/\s+/g, "")
    .replace(/[^\d,.-]/g, "")
    .replace(",", ".");

  const parsed = parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function mapPaidOption(
  row: Record<string, unknown>,
  index: number,
  defaultPriceDomain: string,
): NormalizedOption | null {
  const name = String(row.name || `Opcja ${index + 1}`);
  const rawPrice = row.price;
  const amount = parsePriceToNumber(rawPrice);
  if (amount <= 0) return null;

  const priceType = String(row.price_type || "").toLowerCase();
  const rawPriceString = typeof rawPrice === "string" ? rawPrice.toLowerCase() : "";
  const isBrutto =
    priceType.includes("brutto") ||
    rawPriceString.includes("brutto") ||
    defaultPriceDomain === "brutto";

  const priceNet = isBrutto ? amount / 1.23 : amount;
  const priceGross = isBrutto ? amount : amount * 1.23;

  return {
    name,
    price_net: Number(priceNet.toFixed(2)),
    price_gross: Number(priceGross.toFixed(2)),
    no_discount: Boolean(row.no_discount),
    include_in_wr: Boolean(row.include_in_wr),
  };
}

function isFactoryCategory(category: unknown): boolean {
  const normalized = String(category || "").toLowerCase();
  return !normalized || normalized.includes("fabryczna");
}

function extractOptionsFromPaidOptions(
  paidOptions: unknown,
  defaultPriceDomain?: string,
): { factory: NormalizedOption[]; service: NormalizedOption[] } {
  const rows = Array.isArray(paidOptions) ? paidOptions : [];
  const normalizedDomain = String(defaultPriceDomain || "").toLowerCase();
  const factory: NormalizedOption[] = [];
  const service: NormalizedOption[] = [];

  rows.forEach((rawRow, index) => {
    const row = (rawRow ?? {}) as Record<string, unknown>;
    const mapped = mapPaidOption(row, index, normalizedDomain);
    if (!mapped) return;

    if (isFactoryCategory(row.category)) {
      factory.push({ ...mapped, include_in_wr: false });
      return;
    }

    // Opcje serwisowe są zawsze nierabatowane; include_in_wr steruje WR.
    service.push({ ...mapped, no_discount: false });
  });

  return { factory, service };
}

// ─── CostRow ─────────────────────────────────────────────────────────────────

function CostRow({ label, price }: { label: string; price: number }) {
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="py-1.5 text-xs text-slate-600 font-medium">{label}</td>
      <td className="py-1.5 text-xs text-right font-semibold text-slate-800 tabular-nums">{fmtPLN(price)}</td>
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
  isFetchingTrace,
  onOverridesChange,
  onRecalculate,
  onReset,
  onShowTrace,
}: {
  cell: MiniMatrixCell;
  overrides: CellOverrides;
  isModified: boolean;
  isRecalculating: boolean;
  isFetchingTrace?: boolean;
  onOverridesChange: (o: CellOverrides) => void;
  onRecalculate: () => void;
  onReset: () => void;
  onShowTrace?: () => void;
}) {
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
            {cell.Okres} mc / {(((cell.PrzebiegKontrakt ?? ((cell.Okres / 12) * cell.Przebieg)) / 1000)).toFixed(0)}k km
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
          <div className="text-xs font-bold text-emerald-700">{fmtPLN(cell.WR)} PLN</div>
        </div>
      </div>

      {/* Cost breakdown table */}
      <table className="w-full">
        <thead>
          <tr className="border-b-2 border-slate-200">
            <th className="pb-1 text-xs text-left font-bold text-slate-400 uppercase w-[60%]">Składnik</th>
            <th className="pb-1 text-xs text-right font-bold text-slate-400 uppercase w-[40%]">Cena netto</th>
          </tr>
        </thead>
        <tbody>
          <CostRow label="Finansowanie (PMT)" price={cell.CzynszFinansowy} />
          <CostRow label="Serwis" price={cell.Serwis} />
          <CostRow label="Opony" price={cell.Opony} />
          <CostRow label="Ubezpieczenie" price={cell.Ubezpieczenie} />
          <CostRow label="Samochód zastępczy" price={cell.SamochodZastepczy} />
          <CostRow label="Inne koszty" price={cell.Admin} />
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-slate-300">
            <td className="pt-2 text-xs font-bold text-slate-800">RAZEM (rata LTR)</td>
            <td className="pt-2 text-sm text-right font-bold text-blue-700 tabular-nums">{fmtPLN(cell.LacznaStawka)}</td>
          </tr>
        </tfoot>
      </table>

      {/* Expert Mode Toggle */}
      <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between">
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
        {onShowTrace && (
          <button
            onClick={onShowTrace}
            disabled={isFetchingTrace}
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 disabled:opacity-50"
          >
            {isFetchingTrace ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileCode2 className="w-3.5 h-3.5" />}
            Ślad Przeliczeń (Trace)
          </button>
        )}
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
                value={overrides.custom_months ?? cell.Okres}
                onChange={(v) => update({ custom_months: v > 0 ? v : null })}
                step={6}
                suffix="mc"
                min={6}
              />
              <ExpertNumber
                label="Kilometry/rok"
                value={overrides.custom_km_per_year ?? cell.Przebieg}
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
              <div className="text-lg font-bold text-blue-700 tabular-nums">{fmtPLN(cell.LacznaStawka)} PLN</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function VehicleRowCalculations({ 
  kalkulacjaId, 
  kalkulacjaNumer,
  vehicleId,
  vehicleName = "",
  powertrain = "",
  offerNumber = "",
  configCode = "",
  basePrice = 0
}: { 
  kalkulacjaId: string; 
  kalkulacjaNumer: string;
  vehicleId: string;
  vehicleName?: string;
  powertrain?: string;
  offerNumber?: string;
  configCode?: string;
  basePrice?: number;
}) {
  const [cells, setCells] = useState<MiniMatrixCell[]>([]);
  const [originalCells, setOriginalCells] = useState<MiniMatrixCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCell, setExpandedCell] = useState<string | null>(null);
  const [cellOverrides, setCellOverrides] = useState<Record<number, CellOverrides>>({});
  const [modifiedCells, setModifiedCells] = useState<Set<number>>(new Set());
  const [recalculating, setRecalculating] = useState<number | null>(null);
  const [fetchingTraceCell, setFetchingTraceCell] = useState<number | null>(null);
  const [traceData, setTraceData] = useState<{ krok: string; rownanie: string; wynik: unknown }[] | null>(null);
  const [marginRecalculating, setMarginRecalculating] = useState(false);
  const [matrixView, setMatrixView] = useState<"cards" | "heatmap">("heatmap");
  const [mileageMode, setMileageMode] = useState<MileageMode>("contract");

  // Filter state
  const [filters, setFilters] = useState<MatrixFilters>({
    monthsRange: [12, 84],
    targetKmPerYear: null,
    globalMarginPct: 15.0,
  });

  const mileageReferenceMonths = useMemo(() => {
    const [from, to] = filters.monthsRange;
    if (from === to && from > 0) return from;
    return 48;
  }, [filters.monthsRange]);

  // Store the base payload for per-cell recalculation
  const basePayloadRef = useRef<Payload | null>(null);
  const kmPerMonthRef = useRef<number>(0);



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
      const baseUrl = API_BASE_URL;

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

      const rawBasePrice = String(cardSummary.base_price || cardSummary.total_price || "0");
      const cleanBasePrice = parseFloat(rawBasePrice.replace(/\s+/g, "").replace(",", ".")) || 0;
      
      // Detekcja wariantu brutto
      const priceDomain = cardSummary._price_domain || "unknown";
      const isBrutto = rawBasePrice.toLowerCase().includes("brutto") || priceDomain === "brutto";
      
      const basePriceNet = isBrutto ? parseFloat((cleanBasePrice / 1.23).toFixed(2)) : cleanBasePrice;
      const resolvedVehicleId = vehicleId || stanJson.vehicle_id || kalkData.vehicle_id;
      if (!resolvedVehicleId) {
        throw new Error("Brak vehicle_id w kalkulacji - nie mozna policzyc matrixu.");
      }

                  const persistedFactoryOptions = (stanJson.factory_options || []).map((o: { name: string; price_net: number; price_gross?: number; no_discount?: boolean; include_in_wr?: boolean }) => ({
        name: o.name || "Opcja",
        price_net: o.price_net || 0,
        price_gross: o.price_gross || Number(((o.price_net || 0) * 1.23).toFixed(2)),
        no_discount: Boolean(o.no_discount),
        include_in_wr: false,
      }));

      const persistedServiceOptions = (stanJson.service_options || []).map((o: { name: string; price_net: number; price_gross?: number; no_discount?: boolean; include_in_wr?: boolean }) => ({
        name: o.name || "Usluga",
        price_net: o.price_net || 0,
        price_gross: o.price_gross || Number(((o.price_net || 0) * 1.23).toFixed(2)),
        no_discount: false,
        include_in_wr: Boolean(o.include_in_wr),
      }));

      const fallbackFromPaid = extractOptionsFromPaidOptions(
        cardSummary.paid_options,
        String(cardSummary._price_domain || cardSummary.price_domain || "")
      );

      const normalizedFactoryOptions =
        persistedFactoryOptions.length > 0
          ? persistedFactoryOptions
          : fallbackFromPaid.factory;

      const normalizedServiceOptions =
        persistedServiceOptions.length > 0
          ? persistedServiceOptions
          : fallbackFromPaid.service;

      // 2. Build CalculatorInput payload from stan_json
      const payload: Payload = {
        calculation_id: kalkulacjaId,
        vehicle_id: resolvedVehicleId,
        base_price_net: basePriceNet,
        discount_pct: discount.active_discount_pct || 0,
        factory_options: normalizedFactoryOptions,
        service_options: normalizedServiceOptions,
        okres_bazowy: okresBazowy,
        przebieg_bazowy: przebiegBazowy,
        wibor_pct: financialParams.wibor_pct || 5.0,
        margin_pct: financialParams.margin_pct || 2.0,
        depreciation_pct: financialParams.depreciation_pct || null,
        initial_deposit_pct: financialParams.initial_deposit_pct || 0,
        replacement_car_enabled: toggles.replacement_car !== false,
        add_gsm_subscription: toggles.gps_required !== false,
        add_hook_installation: toggles.hook_installation === true,
        add_grid_dismantling: toggles.grid_dismantling === true,
        add_registration: toggles.add_registration !== false,
        add_sales_prep: toggles.add_sales_prep !== false,
        korekta_kosztu_przygotowania: Number(
          financialParams.sales_prep_correction
            ?? financialParams.korekta_kosztu_przygotowania
            ?? stanJson.korekta_kosztu_przygotowania
            ?? stanJson.KosztPrzygotowaniaDosprzedazyKorekta
            ?? 0
        ),
        z_oponami: toggles.z_oponami !== false,
        klasa_opony_string: stanJson.tire_params?.tire_class || "Medium",
        srednica_felgi: stanJson.tire_params?.rim_diameter || null,
        liczba_kompletow_opon: stanJson.tire_params?.tire_count_mode === "auto" ? null : (isNaN(parseFloat(stanJson.tire_params?.tire_count_mode)) ? null : parseFloat(stanJson.tire_params?.tire_count_mode)),
        korekta_kosztu_opon: stanJson.tire_params?.tire_cost_correction_enabled !== false,
        koszt_opon_korekta: stanJson.tire_params?.tire_cost_correction || 0,
        service_cost_type: stanJson.service_cost_type || "ASO",
        include_servicing: toggles.include_servicing !== false,
        vehicle_vintage: stanJson.vehicle_vintage || "current",
        is_metalic: stanJson.is_metalic === true,
        pricing_margin_pct: financialParams.pricing_margin_pct ?? 15.0,
        manual_wr_correction: 0,
        pakiet_serwisowy: Number(stanJson.pakiet_serwisowy ?? 0),
        inne_koszty_serwisowania_netto: Number(
          financialParams.other_service_costs ?? stanJson.inne_koszty_serwisowania_netto ?? 0
        ),
        matrix_km_mode: mileageMode,
        matrix_contract_km_step: 10000,
        settings: { settings_version_id: null, overrides: null },
        // Przekazanie mocy do kalkulatora backendu (żeby uniknąć 400 Error)
        power_kw: Number(stanJson.power_kw ?? cardSummary.power_kw ?? (cardSummary.power_hp ? Number(cardSummary.power_hp) * 0.73549875 : 0)),
        // Przekazanie parametrów identyfikacyjnych na wypadek braków w BD
        body_type_name: stanJson.body_type_name ?? cardSummary.body_style ?? cardSummary.body_type ?? "",
        zabudowa_type_id: stanJson.zabudowa_type_id ?? ((typeof cardSummary.zabudowa_type_id === "number") ? cardSummary.zabudowa_type_id : null),
        samar_category: stanJson.samar_category ?? cardSummary.samar_category ?? "",
        engine_name: stanJson.engine_category ?? cardSummary.engine_category ?? cardSummary.powertrain ?? "",
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

      // Sync filter margin with the payload's default
      setFilters(prev => ({
        ...prev,
        globalMarginPct: payload.pricing_margin_pct ?? 15.0,
      }));
    } catch (err) {
      console.error("Matrix fetch error:", err);
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setLoading(false);
    }
  }, [kalkulacjaId, vehicleId, mileageMode]);

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
      const baseUrl = API_BASE_URL;

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
      const newCells: MiniMatrixCell[] = data.cells || [];

      // Find the cell matching our effective months
      const foundMonths = ov.custom_months ?? months;
      const targetCell = newCells.find(c => c.Okres === foundMonths);
      if (targetCell) {
        setCells(prev => prev.map(c => c.Okres === months ? targetCell : c));
        setModifiedCells(prev => new Set([...prev, months]));
      }
    } catch (err) {
      console.error("Recalculation error:", err);
    } finally {
      setRecalculating(null);
    }
  }, [cellOverrides]);

  const fetchTraceSingleCell = useCallback(async (months: number, kmYearOverride?: number) => {
    if (!basePayloadRef.current) return;
    const ov = cellOverrides[months] || buildDefaultOverrides(basePayloadRef.current);
    
    setFetchingTraceCell(months);
    try {
      const baseUrl = API_BASE_URL;

      const effectiveMonths = ov.custom_months ?? months;
      const effectiveKmYear = kmYearOverride ?? ov.custom_km_per_year;
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

      const resp = await fetch(`${baseUrl}/api/calculate-trace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd pobierania śladu");
      const data = await resp.json();
      setTraceData(data.calculation_trace || []);
    } catch (err) {
      console.error("Trace error:", err);
      alert("Błąd pobierania śladu: " + err);
    } finally {
      setFetchingTraceCell(null);
    }
  }, [cellOverrides]);

  const resetCell = (months: number) => {
    const original = originalCells.find(c => c.Okres === months);
    if (original) {
      setCells(prev => prev.map(c => c.Okres === months ? original : c));
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

  // ─── Filtered cells (client-side) ──────────────────────────────────

  const filteredCells = useMemo(() => {
    return cells.filter((c) => {
      // Period filter
      if (c.Okres < filters.monthsRange[0] || c.Okres > filters.monthsRange[1]) {
        return false;
      }

      if (filters.targetKmPerYear === null) {
        return true;
      }

      if (mileageMode === "contract") {
        const targetContractKm = (filters.targetKmPerYear / 12) * mileageReferenceMonths;
        const lo = targetContractKm * 0.95;
        const hi = targetContractKm * 1.05;
        const contractKm = c.PrzebiegKontrakt ?? (c.Przebieg / 12) * c.Okres;
        return contractKm >= lo && contractKm <= hi;
      }

      const lo = filters.targetKmPerYear * 0.95;
      const hi = filters.targetKmPerYear * 1.05;
      return c.Przebieg >= lo && c.Przebieg <= hi;
    });
  }, [cells, filters.monthsRange, filters.targetKmPerYear, mileageMode, mileageReferenceMonths]);

  // ─── Global margin recalculation ───────────────────────────────────

  const recalculateWithMargin = useCallback(async (marginPct: number) => {
    if (!basePayloadRef.current) return;
    setMarginRecalculating(true);
    try {
      const baseUrl = API_BASE_URL;
      const modifiedPayload = {
        ...basePayloadRef.current,
        pricing_margin_pct: marginPct,
      };
      const resp = await fetch(`${baseUrl}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });
      if (!resp.ok) throw new Error("Błąd przeliczania matrycy");
      const data = await resp.json();
      const newCells = data.cells || [];
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});
      // Sync filter margin with the payload's default
      setFilters(prev => ({
        ...prev,
        globalMarginPct: marginPct,
      }));
    } catch (err) {
      console.error("Margin recalculation error:", err);
    } finally {
      setMarginRecalculating(false);
    }
  }, []);

  // ─── Exact Variant recalculation ───────────────────────────────────

  const handleExactRecalculate = useCallback(async (months: number, kmPerYear: number, marginPct: number) => {
    if (!basePayloadRef.current) return;
    setMarginRecalculating(true); // Reuse this flag for the toolbar button loading state
    try {
      const baseUrl = API_BASE_URL;
      const targetKm = Math.round((kmPerYear / 12) * months);
      
      const modifiedPayload = {
        ...basePayloadRef.current,
        okres_bazowy: months,
        przebieg_bazowy: targetKm,
        pricing_margin_pct: marginPct,
      };

      const resp = await fetch(`${baseUrl}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd przeliczania wariantu precyzyjnego");
      const data = await resp.json();
      const newCells = data.cells || [];
      
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});

      // Expand the filters to ensure the newly generated cell is visible
      setFilters(prev => ({
        ...prev,
        monthsRange: [
          Math.min(prev.monthsRange[0], months),
          Math.max(prev.monthsRange[1], months)
        ],
        // Set targetKmPerYear to null so it doesn't filter out the new element
        targetKmPerYear: null,
        globalMarginPct: marginPct,
      }));
    } catch (err) {
      console.error("Exact variant recalculation error:", err);
    } finally {
      setMarginRecalculating(false);
    }
  }, []);

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
    <Box sx={{ mt: 4, pt: 4, borderTop: "1px dashed #cbd5e1", backgroundColor: "transparent" }}>
      {/* Top Banner */}
      <Box sx={{ p: 2, mb: 2, bgcolor: "transparent" }}>
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
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
            {/* Added context details */}
            {(offerNumber || configCode || vehicleName) && (
              <div className="flex flex-wrap items-center gap-2 mt-1 pl-9 text-xs text-slate-500 font-medium">
                {offerNumber && (
                  <span className="border border-slate-200 bg-white px-1.5 py-0.5 rounded shadow-sm">Oferta: {offerNumber}</span>
                )}
                {configCode && (
                  <span className="border border-slate-200 bg-white px-1.5 py-0.5 rounded shadow-sm">Kod: {configCode}</span>
                )}
                {vehicleName && (
                  <span className="text-slate-600 ml-1">
                    {vehicleName} {powertrain && `• ${powertrain}`} 
                    {basePrice > 0 && ` • ${fmtPLN(basePrice)} PLN netto`}
                  </span>
                )}
              </div>
            )}
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
      <Box sx={{ px: 0, width: "100%" }}>
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500 bg-slate-50/50 rounded-xl border border-slate-100">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-slate-700">Trwa obliczanie matrycy LTR...</h3>
            <p className="text-xs text-slate-400 mt-1">Proszę czekać, pobieram najnowsze stawki</p>
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
            <div className="flex items-center justify-between mb-3">
              <h3 className="flex items-center text-sm font-bold uppercase tracking-wider text-slate-500">
                <Calculator className="w-4 h-4 mr-2" />
                Matryca rat LTR ({filteredCells.length} / {cells.length} wariantów)
              </h3>
              <MatrixViewToggle view={matrixView} onViewChange={setMatrixView} />
            </div>

            {/* Matrix filter toolbar */}
            <MatrixFilterToolbar
              defaultMarginPct={basePayloadRef.current?.pricing_margin_pct ?? 15.0}
              filters={filters}
              mileageMode={mileageMode}
              onMileageModeChange={setMileageMode}
              referenceMonths={mileageReferenceMonths}
              onFiltersChange={setFilters}
              onMarginRecalculate={recalculateWithMargin}
              onExactRecalculate={handleExactRecalculate}
              isRecalculating={marginRecalculating}
            />

            {/* Reverse price lookup */}
            <ReversePriceLookup basePayload={basePayloadRef.current} />

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

            {/* Matrix View: Heatmap or Cards */}
            {matrixView === "heatmap" ? (
              <MatrixHeatmapView 
                cells={filteredCells} 
                mileageMode={mileageMode} 
                onShowTrace={(cell) => fetchTraceSingleCell(cell.Okres, cell.Przebieg)}
                isFetchingTrace={fetchingTraceCell !== null}
              />
            ) : (
            /* Matrix Card Grid */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {filteredCells.map((cell) => {
                const cellKey = `${cell.Okres}-${cell.Przebieg}`;
                const isExpanded = expandedCell === cellKey;
                const isMod = modifiedCells.has(cell.Okres);

                return (
                  <div key={cellKey} className={isExpanded ? "sm:col-span-2 lg:col-span-3 xl:col-span-4" : ""}>
                    {/* Matrix Cell Card */}
                    <button
                      onClick={() => setExpandedCell(isExpanded ? null : cellKey)}
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
                              {cell.Okres} miesięcy
                            </div>
                            {isMod && <Settings className="w-3 h-3 text-blue-500" />}
                          </div>
                          <div className="text-xs text-slate-400">
                            {mileageMode === "contract"
                              ? `${((cell.PrzebiegKontrakt ?? ((cell.Okres / 12) * cell.Przebieg)) / 1000).toFixed(0)}k km/kontrakt`
                              : `${((cell.PrzebiegKontrakt ?? ((cell.Okres / 12) * cell.Przebieg)) / 1000).toFixed(0)}k km (${cell.Przebieg.toLocaleString("pl-PL")} km/rok)`}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-right">
                            <div className="text-sm font-bold text-blue-700 tabular-nums">
                              {fmtPLN(cell.LacznaStawka)}
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
                        overrides={getOverrides(cell.Okres)}
                        isModified={isMod}
                        isRecalculating={recalculating === cell.Okres}
                        isFetchingTrace={fetchingTraceCell === cell.Okres}
                        onOverridesChange={(o) => handleOverridesChange(cell.Okres, o)}
                        onRecalculate={() => recalculateSingleCell(cell.Okres)}
                        onReset={() => resetCell(cell.Okres)}
                        onShowTrace={() => fetchTraceSingleCell(cell.Okres)}
                      />
                    )}
                  </div>
                );
              })}
            </div>
            )}
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

        {/* Trace Modal */}
        {traceData && (
          <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
                <div className="flex items-center gap-3">
                  <FileCode2 className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-bold text-slate-800 text-lg">Ślad Diagnostyczny (V3 Calculation Trace)</h3>
                </div>
                <button
                  onClick={() => setTraceData(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
                {traceData.length > 0 ? (
                  <div className="space-y-3">
                    {traceData.map((t, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-start gap-4 mb-2">
                          <div className="font-bold text-slate-700 text-sm">
                            <span className="text-slate-400 font-mono text-xs mr-2">[{idx + 1}]</span>
                            {t.krok}
                          </div>
                          <div className="font-mono text-sm font-bold text-blue-700 shrink-0 tabular-nums">
                            {typeof t.wynik === 'number' ? fmtPLN(t.wynik) : String(t.wynik)}
                          </div>
                        </div>
                        {t.rownanie && (
                          <div className="text-xs text-slate-500 font-mono bg-slate-50 p-2 rounded border border-slate-100">
                            {t.rownanie}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-10 text-slate-400">
                    Brak śladu dla tej kalkulacji.
                  </div>
                )}
              </div>
              
            </div>
          </div>
        )}
      </Box>
    </Box>
  );
}





