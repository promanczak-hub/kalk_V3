import { useState } from "react";
import { Chip } from "@mui/material";
import { TrendingUp, RotateCcw, Loader2, FileCode2, Settings } from "lucide-react";
import type { MiniMatrixCell } from "../decision-center/decision-center.types";
import { ExpertNumber, ExpertToggle, ExpertSelect } from "./ExpertControls";
import { InlineTargetPrice } from "./InlineTargetPrice";
import { fmtPLN } from "./calculations.utils";

function SimpleCostRow({ label, price }: { label: string; price: number }) {
  return (
    <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-100/50 transition-colors">
      <td className="py-1 text-xs text-slate-600">{label}</td>
      <td className="py-1 text-xs text-right font-medium text-slate-700 tabular-nums">{fmtPLN(price)}</td>
    </tr>
  );
}
import type { CellOverrides } from "./useVehicleCalculations";

interface CellDetailProps {
  cell: MiniMatrixCell;
  overrides: CellOverrides;
  isModified: boolean;
  isRecalculating: boolean;
  isFetchingTrace?: boolean;
  onOverridesChange: (o: CellOverrides) => void;
  onRecalculate: () => void;
  onReset: () => void;
  onShowTrace?: () => void;
}

export function CellDetail({
  cell,
  overrides,
  isModified,
  isRecalculating,
  isFetchingTrace,
  onOverridesChange,
  onRecalculate,
  onReset,
  onShowTrace,
}: CellDetailProps) {
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
          <SimpleCostRow label="Finansowanie (PMT)" price={cell.CzynszFinansowy} />
          <SimpleCostRow label="Serwis" price={cell.Serwis} />
          <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-100/50 transition-colors">
            <td className="py-1 text-xs text-slate-600 flex items-center gap-2">
              Opony
              {overrides.tire_cost_correction_brutto != null && (
                <span className="text-[9px] bg-sky-100 text-sky-700 px-1 py-0.5 rounded font-bold" title="Aktywna manualna korekta kosztu opon na cały kontrakt (brutto)">NADPISANE</span>
              )}
            </td>
            <td className="py-1 text-xs text-right font-medium text-slate-700 tabular-nums">
              <div className="flex items-center justify-end gap-2">
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step={100}
                    placeholder="Całość Brutto"
                    value={overrides.tire_cost_correction_brutto ?? ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      update({ tire_cost_correction_brutto: val === "" ? null : Number(val) });
                    }}
                    onBlur={() => onRecalculate()}
                    className="w-24 text-[10px] p-0.5 border border-slate-200 rounded text-right outline-none focus:ring-1 focus:ring-blue-400 bg-white transition-all hover:border-blue-300"
                    title="Wpisz całkowity koszt opon na cały kontrakt w PLN BRUTTO. Naciśnij Przelicz lub użyj poza polem, by zaktualizować."
                  />
                  <span className="text-[9px] text-slate-400">brutto</span>
                </div>
                <span className="w-16">{fmtPLN(cell.Opony)}</span>
              </div>
            </td>
          </tr>
          <SimpleCostRow label="Ubezpieczenie" price={cell.Ubezpieczenie} />
          <SimpleCostRow label="Samochód zastępczy" price={cell.SamochodZastepczy} />
          <SimpleCostRow label="Inne koszty" price={cell.Admin} />
          <tr className="border-t border-slate-200">
            <td className="py-2 text-[10px] font-bold text-slate-400 uppercase">Suma Serwis (Krok 4+5)</td>
            <td className="py-2 text-xs text-right font-bold text-slate-600 tabular-nums">
              {fmtPLN(cell.Serwis + (cell.OpcjeSerwisoweSumaNetto / cell.Okres))}
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-slate-300">
            <td className="pt-2 text-xs font-bold text-slate-800">RAZEM (rata LTR)</td>
            <td className="pt-2 text-sm text-right font-bold text-blue-700 tabular-nums">{fmtPLN(cell.LacznaStawka)}</td>
          </tr>
        </tfoot>
      </table>

      {/* ── KOREKTA WR (always visible) ─────────────────────────────── */}
      <div className="mt-3 pt-3 border-t border-slate-200">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">🔧 Korekta WR</span>
          {overrides.manual_wr_correction !== 0 && (
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
              style={{
                background:
                  overrides.manual_wr_correction > 0
                    ? "rgba(234,179,8,0.15)"
                    : "rgba(239,68,68,0.12)",
                color:
                  overrides.manual_wr_correction > 0 ? "#b45309" : "#dc2626",
              }}
            >
              AKTYWNA{" "}
              {overrides.manual_wr_correction > 0 ? "+" : ""}
              {overrides.manual_wr_correction.toLocaleString("pl-PL")} PLN
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <input
            type="number"
            step={500}
            value={overrides.manual_wr_correction}
            onChange={(e) =>
              update({ manual_wr_correction: parseFloat(e.target.value) || 0 })
            }
            className="w-28 text-xs p-1.5 border border-slate-200 rounded text-right outline-none focus:ring-1 focus:ring-blue-400 tabular-nums bg-white"
          />
          <span className="text-[10px] text-slate-400">PLN</span>
          <button
            onClick={onRecalculate}
            disabled={isRecalculating}
            className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRecalculating ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <TrendingUp className="w-3 h-3" />
            )}
            Przelicz
          </button>
          {isModified && (
            <button
              onClick={onReset}
              className="flex items-center gap-1 text-[11px] font-medium px-2 py-1.5 rounded-md bg-slate-100 text-slate-500 hover:bg-slate-200 transition-all border border-slate-200"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
          <div className="ml-auto text-right">
            <div className="text-[9px] text-slate-400">WR po korekcie</div>
            <div
              className="text-xs font-bold tabular-nums"
              style={{ color: overrides.manual_wr_correction >= 0 ? "#059669" : "#dc2626" }}
            >
              {overrides.manual_wr_correction !== 0
                ? `${fmtPLN(cell.WR + overrides.manual_wr_correction)} PLN`
                : `${fmtPLN(cell.WR)} PLN`}
            </div>
          </div>
        </div>
        <p className="mt-1 text-[9px] text-slate-400">
          Korekta ręczna WR: wyższa wartość rezydualna → niższy czynsz techniczny
        </p>
      </div>

      {/* ── CEL CENOWY (zero dodatkowych API calls) ──────────────────── */}
      <InlineTargetPrice cell={cell} />

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
                value={overrides.pricing_margin_pct ?? ""}
                onChange={(v) => update({ pricing_margin_pct: v === "" ? null : Number(v) })}
                step={0.5}
                suffix="%"
                min={0}
              />
              <ExpertNumber
                label="Okres (mc)"
                value={overrides.custom_months ?? cell.Okres ?? ""}
                onChange={(v) => update({ custom_months: v === "" ? null : Number(v) > 0 ? Number(v) : null })}
                step={6}
                suffix="mc"
                min={6}
              />
              <ExpertNumber
                label="Kilometry/rok"
                value={overrides.custom_km_per_year ?? cell.Przebieg}
                onChange={(v) => update({ custom_km_per_year: Number(v) > 0 ? Number(v) : null })}
                step={5000}
                suffix="km"
                min={5000}
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
                value={overrides.pakiet_serwisowy ?? ""}
                onChange={(v) => update({ pakiet_serwisowy: v === "" ? 0 : Number(v) })}
                step={100}
                suffix="PLN"
                min={0}
              />
              <ExpertNumber
                label="Inne koszty mc"
                value={overrides.inne_koszty_serwisowania_netto ?? ""}
                onChange={(v) => update({ inne_koszty_serwisowania_netto: v === "" ? 0 : Number(v) })}
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
                checked={overrides.z_oponami}
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
                checked={overrides.replacement_car_enabled}
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
