/**
 * ValidationWarningsCard
 *
 * Collapsible audit panel showing ALL warnings from `synthesis_data._validation.warnings[]`.
 *
 * Validator produces 13 deterministic rules covering: price sanity, base+options
 * vs total, discount triangulation, net/gross ratio, service_equipment integrity,
 * power consistency, dealer extras detection. This card surfaces every finding
 * (DiscountAuditCard only shows the discount-related subset).
 *
 * Early-returns `null` when there are no warnings — clean extractions show no UI.
 */

import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
} from "lucide-react";
import type { PriceValidation, PriceValidationWarning } from "../../types";

interface ValidationWarningsCardProps {
  validation: PriceValidation | null | undefined;
}

type Severity = "ERROR" | "WARNING" | "INFO";

// Human-readable labels for validator rule codes
const RULE_LABELS: Record<string, string> = {
  // Price sanity (Rules 1-7)
  PRICE_OUT_OF_REALISTIC_RANGE: "Cena poza realistycznym zakresem",
  BASE_PLUS_OPTIONS_VS_TOTAL: "Baza + opcje ≠ cena całkowita",
  OPTIONS_SUM_MISMATCH: "Suma opcji ≠ deklarowane options_price",
  SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE: "Pojedyncza opcja > 50% bazy",
  BASE_GT_TOTAL: "Baza większa niż cena całkowita",
  BASE_TOTAL_SWAP_DETECTED: "Wykryto zamianę base ↔ total",
  UNPARSEABLE_OPTION_PRICE: "Cena opcji nieczytelna",
  // Power (Rule 8)
  POWER_KW_HP_MISMATCH: "Niespójność mocy (kW × 1,36 ≠ KM)",
  // Discount (Rules 9-11)
  DISCOUNT_TRIANGULATION_FAILED: "Rabat: triangulacja nie zgadza się",
  DISCOUNT_COMPUTED_INDIRECTLY: "Rabat wyliczony pośrednio",
  DEALER_EXTRAS_IN_DISCOUNTABLE: "Zabudowa wykryta w opcjach rabatowanych",
  DISCOUNT_PCT_OUT_OF_RANGE: "Procent rabatu poza zakresem",
  // Net/Gross (Rules 12-13)
  NET_GROSS_RATIO_INVALID: "Stosunek brutto/netto poza ~1,23",
  SERVICE_EQUIPMENT_SUM_MISMATCH: "Suma componentów ≠ total service_equipment",
  // Price domain
  PRICE_DOMAIN_UNKNOWN: "Nieznana domena cenowa (netto/brutto)",
  // Self-healing
  AUTO_FIX_APPLIED: "Auto-korekta zastosowana",
  DISCOUNT_DETECTED: "Wykryto rabat z różnicy cen",
};

const SEVERITY_CONFIG: Record<
  Severity,
  {
    label: string;
    icon: typeof AlertTriangle;
    bg: string;
    bgRow: string;
    text: string;
    border: string;
  }
> = {
  ERROR: {
    label: "Błąd",
    icon: AlertCircle,
    bg: "bg-red-100",
    bgRow: "bg-red-50/60",
    text: "text-red-700",
    border: "border-red-200",
  },
  WARNING: {
    label: "Ostrzeżenie",
    icon: AlertTriangle,
    bg: "bg-amber-100",
    bgRow: "bg-amber-50/60",
    text: "text-amber-700",
    border: "border-amber-200",
  },
  INFO: {
    label: "Info",
    icon: Info,
    bg: "bg-sky-100",
    bgRow: "bg-sky-50/60",
    text: "text-sky-700",
    border: "border-sky-200",
  },
};

function WarningRow({ w }: { w: PriceValidationWarning }) {
  const cfg = SEVERITY_CONFIG[w.severity];
  const Icon = cfg.icon;
  const label = RULE_LABELS[w.rule] ?? w.rule;
  return (
    <div className={`p-2.5 rounded border ${cfg.border} ${cfg.bgRow}`}>
      <div className="flex items-start gap-2">
        <Icon className={`w-4 h-4 ${cfg.text} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className={`text-xs font-semibold ${cfg.text}`}>{label}</span>
            <code className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1 rounded">
              {w.rule}
            </code>
          </div>
          <div className="text-xs text-slate-700 leading-snug">{w.message}</div>
          {(w.expected !== undefined || w.actual !== undefined || w.diff_pct !== undefined) && (
            <div className="mt-1 flex gap-3 text-[10px] text-slate-500 font-mono">
              {w.expected !== undefined && (
                <span>expected: <strong className="text-slate-700">{w.expected.toLocaleString("pl-PL", { maximumFractionDigits: 2 })}</strong></span>
              )}
              {w.actual !== undefined && (
                <span>actual: <strong className="text-slate-700">{w.actual.toLocaleString("pl-PL", { maximumFractionDigits: 2 })}</strong></span>
              )}
              {w.diff_pct !== undefined && (
                <span>Δ: <strong className="text-slate-700">{w.diff_pct.toFixed(2)}%</strong></span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ValidationWarningsCard({
  validation,
}: ValidationWarningsCardProps) {
  const [open, setOpen] = useState(false);

  const grouped = useMemo(() => {
    const warnings = validation?.warnings ?? [];
    const errors = warnings.filter((w) => w.severity === "ERROR");
    const warns = warnings.filter((w) => w.severity === "WARNING");
    const infos = warnings.filter((w) => w.severity === "INFO");
    return { errors, warns, infos, total: warnings.length };
  }, [validation]);

  // Early return — clean validation = no UI
  if (!validation || grouped.total === 0) return null;

  // Decide header color: ERROR > WARNING > INFO
  const headerSeverity: Severity =
    grouped.errors.length > 0
      ? "ERROR"
      : grouped.warns.length > 0
        ? "WARNING"
        : "INFO";
  const cfg = SEVERITY_CONFIG[headerSeverity];
  const Icon = cfg.icon;

  const summaryChips = [
    grouped.errors.length > 0 && {
      label: `${grouped.errors.length} ${grouped.errors.length === 1 ? "błąd" : "błędów"}`,
      cls: "bg-red-100 text-red-700",
    },
    grouped.warns.length > 0 && {
      label: `${grouped.warns.length} ostrzeżeń`,
      cls: "bg-amber-100 text-amber-700",
    },
    grouped.infos.length > 0 && {
      label: `${grouped.infos.length} info`,
      cls: "bg-sky-100 text-sky-700",
    },
  ].filter(Boolean) as Array<{ label: string; cls: string }>;

  return (
    <div className={`w-full rounded-lg border ${cfg.border} bg-white shadow-sm`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 p-3 hover:bg-slate-50 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <Icon className={`w-4 h-4 ${cfg.text}`} />
          <span className="text-sm font-semibold text-slate-700">
            Audyt techniczny ekstrakcji
          </span>
          {summaryChips.map((c, i) => (
            <span
              key={i}
              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${c.cls}`}
            >
              {c.label}
            </span>
          ))}
          {validation.is_valid && grouped.errors.length === 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 font-medium">
              <CheckCircle2 className="w-3 h-3" />
              dane prawidłowe matematycznie
            </span>
          )}
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {open && (
        <div className="border-t border-slate-100 p-3 space-y-2 animate-in fade-in slide-in-from-top-1 duration-150">
          {validation.summary?.details && (
            <div className="text-xs text-slate-600 italic bg-slate-50 p-2 rounded">
              {validation.summary.details}
            </div>
          )}
          {grouped.errors.length > 0 && (
            <div className="space-y-1.5">
              {grouped.errors.map((w, i) => (
                <WarningRow key={`err-${i}`} w={w} />
              ))}
            </div>
          )}
          {grouped.warns.length > 0 && (
            <div className="space-y-1.5">
              {grouped.warns.map((w, i) => (
                <WarningRow key={`warn-${i}`} w={w} />
              ))}
            </div>
          )}
          {grouped.infos.length > 0 && (
            <div className="space-y-1.5">
              {grouped.infos.map((w, i) => (
                <WarningRow key={`info-${i}`} w={w} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
