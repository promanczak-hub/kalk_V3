import { AlertTriangle, AlertOctagon, Info, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { PriceValidation, PriceValidationWarning } from "../../types";

interface PriceValidationBannerProps {
  validation: PriceValidation;
}

const SEVERITY_CONFIG = {
  ERROR: {
    icon: AlertOctagon,
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-800",
    badge: "bg-red-100 text-red-700",
    iconColor: "text-red-500",
  },
  WARNING: {
    icon: AlertTriangle,
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-800",
    badge: "bg-amber-100 text-amber-700",
    iconColor: "text-amber-500",
  },
  INFO: {
    icon: Info,
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-800",
    badge: "bg-blue-100 text-blue-700",
    iconColor: "text-blue-500",
  },
} as const;

function maxSeverity(warnings: PriceValidationWarning[]): "ERROR" | "WARNING" | "INFO" {
  if (warnings.some((w) => w.severity === "ERROR")) return "ERROR";
  if (warnings.some((w) => w.severity === "WARNING")) return "WARNING";
  return "INFO";
}

function fmtNum(n: number): string {
  return n.toLocaleString("pl-PL", { maximumFractionDigits: 0 });
}

export function PriceValidationBanner({ validation }: PriceValidationBannerProps) {
  const [expanded, setExpanded] = useState(false);

  if (validation.is_valid || validation.warnings.length === 0) {
    return null;
  }

  const severity = maxSeverity(validation.warnings);
  const config = SEVERITY_CONFIG[severity];
  const Icon = config.icon;

  const errorCount = validation.warnings.filter((w) => w.severity === "ERROR").length;
  const warnCount = validation.warnings.filter((w) => w.severity === "WARNING").length;

  const summaryParts: string[] = [];
  if (errorCount > 0) summaryParts.push(`${errorCount} błąd${errorCount > 1 ? "y" : ""}`);
  if (warnCount > 0) summaryParts.push(`${warnCount} ostrzeżeń`);

  return (
    <div className={`${config.bg} ${config.border} border rounded-lg overflow-hidden`}>
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center justify-between px-4 py-2.5 ${config.text} hover:opacity-80 transition-opacity`}
      >
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${config.iconColor} flex-shrink-0`} />
          <span className="text-xs font-semibold">
            Walidacja cenowa: {summaryParts.join(", ")}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${config.badge}`}>
            {severity}
          </span>
          {expanded ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </div>
      </button>

      {/* Detail — expandable */}
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {validation.warnings.map((w, idx) => {
            const wConfig = SEVERITY_CONFIG[w.severity];
            const WIcon = wConfig.icon;
            return (
              <div
                key={`${w.rule}-${idx}`}
                className="flex items-start gap-2 text-xs leading-relaxed"
              >
                <WIcon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${wConfig.iconColor}`} />
                <div className={wConfig.text}>
                  <span className="font-medium">{w.rule}</span>
                  <span className="mx-1">—</span>
                  <span>{w.message}</span>
                  {w.diff_pct != null && (
                    <span className={`ml-1 ${wConfig.badge} px-1.5 py-0.5 rounded text-[10px] font-mono`}>
                      Δ {w.diff_pct.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            );
          })}

          {/* Parsed prices summary */}
          {validation.parsed_prices && (
            <div className="mt-2 pt-2 border-t border-current/10 flex gap-4 text-[10px] text-slate-500 font-mono">
              {validation.parsed_prices.base != null && (
                <span>baza: {fmtNum(validation.parsed_prices.base)}</span>
              )}
              {validation.parsed_prices.options != null && (
                <span>opcje: {fmtNum(validation.parsed_prices.options)}</span>
              )}
              {validation.parsed_prices.total != null && (
                <span>total: {fmtNum(validation.parsed_prices.total)}</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
