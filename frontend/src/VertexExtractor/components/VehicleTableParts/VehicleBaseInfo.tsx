import React, { useState, useCallback, useMemo } from "react";
import { ChevronUp, ChevronDown, Check, AlertTriangle, Copy, CheckCheck, Edit3, Car } from "lucide-react";
import { format } from "date-fns";
import type { FleetVehicleView } from "../../types";
import type { DiscountAlert } from "../../hooks/useDiscountAlerts";
export interface MappedData {
  brand: string;
model: string;
fuel: string;
vehicle_type: string;
trim_level: string;
transmission: string;
samar_category?: string;
engine_class?: string;
drive_type?: string;
  body_type?: string;
  body_candidates?: { klasa: string; confidence: number }[];
}

export interface SamarCandidate {
  klasa: string;
  confidence: number;
}

export interface EngineCandidate {
  klasa: string;
  confidence: number;
}

interface VehicleBaseInfoProps {
  vehicle: FleetVehicleView;
  isExpanded: boolean;
  onToggleExpand: () => void;
  activeFinalPriceNet: number;
  totalCatalogPriceNet: number;
  formatCalculatedPrice: (val: number) => string;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  onConfigurationCodeChange?: (newCode: string) => void;
  crossCardAlerts?: DiscountAlert[];
  onScrollToVehicle?: (vehicleId: string) => void;

  discountMode?: "offer" | "suggested" | "custom";
  setDiscountMode?: (mode: "offer" | "suggested" | "custom") => void;
  customDiscountPctRaw?: string | number;
  setCustomDiscountPctRaw?: (val: string) => void;
  offerDiscountPercentage?: number;
  suggestedDiscountPct?: number;

  technicalDescription?: string;
}

function hasValue(v: string | null | undefined): boolean {
return Boolean(v && v !== "Brak" && v !== "-");
}

export function Tag({ children, connected, icon: Icon }: { children: React.ReactNode; connected?: boolean; icon?: React.ElementType }) {
return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium text-slate-600 ${connected ? "justify-center h-full px-2.5 py-1 text-[11px] bg-slate-50/50" : "bg-slate-50 px-2.5 py-1 text-xs border border-slate-200 rounded"}`}
      style={{ fontFamily: "'Geist Mono', monospace", lineHeight: 1 }}
    >
      {Icon && <Icon className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />}
      {children}
    </span>
);
}



const DRIVE_TYPE_OPTIONS = [
{ value: "4x2 (FWD)", label: "4x2 (FWD)" },
{ value: "4x2 (RWD)", label: "4x2 (RWD)" },
{ value: "4x4 (AWD)", label: "4x4 (AWD)" },
];

export function DriveTypeTag({ current, onChange, connected }: { current: string; onChange?: (v: string) => void; connected?: boolean }) {
if (!onChange) {
    return current ? <Tag connected={connected}>{current}</Tag> : null;
}
return (
    <span className="inline-flex items-center h-full">
      <select
        className={`bg-slate-50/50 font-medium text-slate-600 cursor-pointer hover:bg-slate-100 focus:outline-none focus:ring-inset focus:ring-1 focus:ring-indigo-400 ${connected ? "h-full px-2.5 text-[11px] border-0" : "px-1.5 py-1 text-xs border border-slate-200 rounded"}`}
        style={{ fontFamily: "'Geist Mono', monospace" }}
        value={current || ""}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => { e.stopPropagation(); onChange(e.target.value); }}
      >
        <option value="" disabled>Oś napędowa...</option>
        {DRIVE_TYPE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </span>
);
}

const TRANSMISSION_OPTIONS = [
  { value: "Automatyczna", label: "Automatyczna" },
  { value: "Manualna", label: "Manualna" },
];

export function TransmissionTag({ current, onChange, connected }: { current: string; onChange?: (v: string) => void; connected?: boolean }) {
  if (!onChange) {
      return current ? <Tag connected={connected}>{current}</Tag> : null;
  }
  return (
      <span className="inline-flex items-center h-full">
        <select
          className={`bg-slate-50/50 font-medium text-slate-600 cursor-pointer hover:bg-slate-100 focus:outline-none focus:ring-inset focus:ring-1 focus:ring-indigo-400 ${connected ? "h-full px-2.5 text-[11px] border-0" : "px-1.5 py-1 text-xs border border-slate-200 rounded"}`}
          style={{ fontFamily: "'Geist Mono', monospace" }}
          value={current || ""}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => { e.stopPropagation(); onChange(e.target.value); }}
        >
          <option value="" disabled>Skrzynia...</option>
          {TRANSMISSION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </span>
  );
}

/** Fallback body type options — used only when DB data hasn't loaded yet */
const BODY_TYPE_FALLBACK = [
"Hatchback", "Sedan", "Kombi", "SUV", "Liftback", "Coupe", "Cabrio", "Minivan",
"Wieloosobowy", "Pickup", "Furgon", "Podwozie",
];

const BODY_TYPE_ALIAS_MAP: Record<string, string> = {
"SPORTSTOURER": "Kombi",
"SPORTS TOURER": "Kombi",
"TOURING": "Kombi",
"AVANT": "Kombi",
"ESTATE": "Kombi",
"WAGON": "Kombi",
"VARIANT": "Kombi",
"SPORTSWAGON": "Kombi",
"PANEL VAN": "Furgon",
"VAN": "Furgon",
"CARGO": "Furgon",
"PICK-UP": "Pickup",
};

function normalizeBodyTypeValue(value: string): string {
const trimmed = (value || "").trim();
if (!trimmed) return "";
const upper = trimmed.toUpperCase();
return BODY_TYPE_ALIAS_MAP[upper] || trimmed;
}

export function BodyTypeTag({ current, dbOptions, onChange, connected, currentVehicleType }: {
  current: string;
  dbOptions?: { name: string; vehicle_class: string }[];
  onChange?: (v: string) => void;
  connected?: boolean;
  currentVehicleType?: string;
}) {
  const normValue = normalizeBodyTypeValue(current);
  
  const options = useMemo(() => {
    if (!dbOptions || dbOptions.length === 0) return BODY_TYPE_FALLBACK;
    // Filter by vehicle_class if provided
    let filtered = dbOptions;
    if (currentVehicleType) {
      const typeLower = currentVehicleType.toLowerCase();
      const isCommercial = typeLower.includes("commercial") || 
                           typeLower.includes("dostawcz") ||
                           typeLower.includes("ciężar") ||
                           typeLower.includes("ciezar");
      filtered = dbOptions.filter(o => {
        const oClass = (o.vehicle_class || "").toLowerCase();
        if (isCommercial) return oClass.includes("commercial") || oClass.includes("dostawcz") || oClass.includes("ciężar") || oClass.includes("ciezar");
        return oClass.includes("passenger") || oClass.includes("osobow");
      });
      if (filtered.length === 0) filtered = dbOptions;
    }
    return Array.from(new Set(filtered.map(o => o.name))).sort();
  }, [dbOptions, currentVehicleType]);

  if (!onChange) {
    return current ? <Tag connected={connected} icon={Car}>{normValue}</Tag> : null;
  }

  return (
    <span className="inline-flex items-center h-[26px] bg-slate-50/50 pl-2 pr-1 rounded">
      <Car className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mr-1.5" />
      <select
        className={`bg-transparent font-medium text-slate-600 cursor-pointer hover:bg-slate-100 focus:outline-none focus:ring-inset focus:ring-1 focus:ring-indigo-400 ${connected ? "h-full text-[11px] border-0" : "text-xs border-0 py-0.5"}`}
        style={{ fontFamily: "'Geist Mono', monospace" }}
        value={normValue || ""}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => { e.stopPropagation(); onChange(e.target.value); }}
      >
        <option value="" disabled>Nadwozie...</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </span>
  );
}


/** Monospace VT323 tag for offer/config codes - click to copy */
function CodeTag({ children }: { children: React.ReactNode }) {
const [copied, setCopied] = useState(false);

const handleCopy = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      const text = typeof children === "string" ? children : ((e.currentTarget as HTMLElement).textContent || "");
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      });
    },
    [children],
);

return (
    <span
      className={`inline-flex items-center gap-1 border px-2.5 py-1 rounded text-sm tracking-wide cursor-pointer transition-colors ${
        copied
          ? "border-green-400 bg-green-50 text-green-700"
          : "border-slate-300 bg-slate-100 text-slate-700 hover:bg-slate-200 hover:border-slate-400"
      }`}
      style={{ fontFamily: "'Geist Mono', monospace" }}
      onClick={handleCopy}
      title="Kliknij, aby skopiować"
    >
      {children}
      {copied ? (
        <CheckCheck className="w-3 h-3 text-green-600" />
      ) : (
        <Copy className="w-3 h-3 text-slate-400" />
      )}
    </span>
);
}

export function VehicleBaseInfo({
  vehicle,
  isExpanded,
  onToggleExpand,
  activeFinalPriceNet,
  totalCatalogPriceNet,
  formatCalculatedPrice,

  isSelected = false,
  onToggleSelect,
  crossCardAlerts = [],
  onScrollToVehicle,

  onConfigurationCodeChange,
  discountMode,
  setDiscountMode,
  customDiscountPctRaw,
  setCustomDiscountPctRaw,
  offerDiscountPercentage = 0,
  suggestedDiscountPct = 0,
  technicalDescription,
}: VehicleBaseInfoProps) {
  return (
    <div
      className="p-3 sm:py-3 sm:px-4 cursor-pointer select-none"
      onClick={onToggleExpand}
    >
      <div className="flex items-start gap-3 justify-between">
        
        {/* Lewa strona: Checkbox + Data + Dane pojazdu */}
        <div className="flex items-start gap-3 min-w-0 flex-grow">
          {onToggleSelect && (
            <div
              className="flex-shrink-0 mt-0.5"
              onClick={(e) => {
                e.stopPropagation();
                onToggleSelect();
              }}
            >
              <div
                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors cursor-pointer ${
                  isSelected
                    ? "bg-blue-500 border-blue-500"
                    : "border-slate-300 hover:border-blue-400"
                }`}
              >
                {isSelected && <Check className="w-3 h-3 text-white" />}
              </div>
            </div>
          )}

          <span className="text-xs text-slate-400 tabular-nums whitespace-nowrap hidden sm:inline mt-1" style={{ fontFamily: "'Geist Mono', monospace" }}>
            {format(new Date(vehicle.created_at), "dd.MM.yyyy")}
          </span>

          <div className="min-w-0 flex flex-col gap-2">
            {/* Tytuł */}
            <div className="flex items-baseline gap-2 flex-wrap">
              <h3 className="text-sm font-semibold text-slate-900 truncate">
                {vehicle.brand || "?"} {vehicle.model}
              </h3>
              {hasValue(vehicle.trim_level) && (
                <span className="text-xs text-slate-500 font-medium">{vehicle.trim_level}</span>
              )}
              <span className="text-xs text-slate-500 max-w-full break-words" style={{ fontFamily: "'Geist Mono', monospace" }}>
                {technicalDescription || (hasValue(vehicle.powertrain) ? vehicle.powertrain : "Brak danych specyfikacji")}
              </span>
            </div>
            
            {/* Sub-informacje w jednym rzędzie: napęd, kody, rabaty */}
            <div className="flex items-center gap-x-4 gap-y-2 flex-wrap">

              <div className="flex items-center gap-1.5 flex-wrap">
                {hasValue(vehicle.offer_number) && (
                  <CodeTag>{vehicle.offer_number}</CodeTag>
                )}
                {onConfigurationCodeChange ? (
                  <div className="flex items-center gap-1 border border-slate-300 bg-slate-100 px-2 py-0.5 rounded text-xs group/edit focus-within:ring-2 focus-within:ring-blue-400 focus-within:border-blue-400 transition-all shadow-sm">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">CONFIG</span>
                    <input
                      type="text"
                      defaultValue={vehicle.configuration_code || ""}
                      onBlur={(e) => {
                        if (e.target.value !== vehicle.configuration_code) {
                          onConfigurationCodeChange(e.target.value);
                        }
                      }}
                      className="bg-transparent border-none outline-none text-slate-700 font-mono text-[11px] w-20 focus:w-32 transition-all p-0"
                      style={{ fontFamily: "'Geist Mono', monospace" }}
                      placeholder="Kod..."
                    />
                    <Edit3 className="w-3 h-3 text-slate-400 opacity-0 group-hover/edit:opacity-100 transition-opacity" />
                  </div>
                ) : hasValue(vehicle.configuration_code) && (
                  <CodeTag>{vehicle.configuration_code}</CodeTag>
                )}
              </div>

              {/* Rabat Controls */}
              {discountMode ? (
                <div className="flex h-[24px] bg-slate-50 border border-slate-200 rounded text-[11px] font-medium text-slate-600 overflow-hidden divide-x divide-slate-200 shadow-sm">
                  <button
                    type="button"
                    className={`px-2 flex items-center transition-colors hover:bg-slate-100 ${
                      discountMode === "offer" ? "bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold" : ""
                    }`}
                    onClick={(e) => { e.stopPropagation(); setDiscountMode?.("offer"); }}
                    title="Rabat z oferty sprzedawcy"
                  >
                    <span className="mr-1 hidden sm:inline">Oferta:</span>
                    <span>{offerDiscountPercentage.toFixed(1)}%</span>
                  </button>
                  <button
                    type="button"
                    className={`px-2 flex items-center transition-colors hover:bg-slate-100 ${
                      discountMode === "suggested" ? "bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold" : ""
                    }`}
                    onClick={(e) => { e.stopPropagation(); setDiscountMode?.("suggested"); }}
                    title="Sugerowany rabat Express"
                  >
                    <span className="mr-1 hidden sm:inline">Express:</span>
                    <span>{(suggestedDiscountPct).toFixed(1)}%</span>
                  </button>
                  <div
                    className={`flex items-center transition-colors hover:bg-slate-100 cursor-pointer ${
                      discountMode === "custom" ? "bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold pl-1.5" : "px-2"
                    }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (discountMode !== "custom") setDiscountMode?.("custom");
                    }}
                    title="Własny rabat (kliknij aby edytować)"
                  >
                    <span className={discountMode === "custom" ? "mr-1 hidden sm:inline" : "hidden sm:inline"}>Własny:</span>
                    {discountMode === "custom" ? (
                      <div className="flex items-center pl-1 bg-white border-l border-blue-200 h-full">
                        <input
                          type="number"
                          step="0.1"
                          className="w-10 h-full bg-transparent text-right outline-none px-1 text-blue-900 font-mono text-[11px]"
                          value={customDiscountPctRaw || ""}
                          onChange={(e) => setCustomDiscountPctRaw?.(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          autoFocus
                        />
                        <span className="pr-1.5 text-blue-900">%</span>
                      </div>
                    ) : (
                      <span>{customDiscountPctRaw || "0"}%</span>
                    )}
                  </div>
                </div>
              ) : vehicle.suggested_discount_pct != null ? (
                <Tag>Rabat: {vehicle.suggested_discount_pct}%</Tag>
              ) : vehicle.synthesis_data ? (
                <Tag>Brak rabatu</Tag>
              ) : null}

              {crossCardAlerts.length > 0 && (
                <button
                  type="button"
                  className="inline-flex items-center gap-1 border border-amber-300 bg-amber-50 px-2 py-0.5 h-[24px] rounded text-[11px] font-semibold text-amber-700 hover:bg-amber-100 hover:border-amber-400 transition-colors cursor-pointer animate-in fade-in duration-300 shadow-sm"
                  title={`Kliknij, aby przewinąć do oferty ${crossCardAlerts[0].siblingOfferNumber || "(brak nr)"}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    const targetId = crossCardAlerts[0].siblingVehicleId;
                    if (onScrollToVehicle) onScrollToVehicle(targetId);
                  }}
                >
                  <AlertTriangle className="w-3 h-3" />
                  Lepszy rabat (+{crossCardAlerts[0].deltaPp} pp.)
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Prawa strona: Cena + Chevron */}
        <div className="flex items-start gap-4 flex-shrink-0">
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold" style={{ fontFamily: "'Geist Mono', monospace" }}>
              {activeFinalPriceNet > 0 && activeFinalPriceNet !== totalCatalogPriceNet ? "SUMA CAŁKOWITA" : totalCatalogPriceNet > 0 ? "CENA KATALOGOWA" : ""}
            </span>
            {(activeFinalPriceNet > 0 || totalCatalogPriceNet > 0) ? (
              <>
                <span className="text-base sm:text-lg font-bold text-slate-900 tabular-nums tracking-tight leading-none mt-0.5" style={{ fontFamily: "'Geist Mono', monospace" }}>
                  {formatCalculatedPrice(activeFinalPriceNet > 0 ? activeFinalPriceNet : totalCatalogPriceNet)}{" "}
                  <span className="text-[10px] font-semibold text-slate-500">PLN BRUTTO</span>
                </span>
                <span className="text-[11px] text-slate-400 tabular-nums mt-1 leading-none" style={{ fontFamily: "'Geist Mono', monospace" }}>
                  {formatCalculatedPrice(Math.round((activeFinalPriceNet > 0 ? activeFinalPriceNet : totalCatalogPriceNet) / 1.23))} PLN NETTO
                </span>
              </>
            ) : (
              <span className="text-sm text-slate-400 mt-1" style={{ fontFamily: "'Geist Mono', monospace" }}>Brak wyceny</span>
            )}
          </div>

          <div className="text-slate-400 group-hover:text-blue-500 transition-colors bg-slate-50 group-hover:bg-blue-50 rounded-full p-1 border border-transparent group-hover:border-blue-100 mt-1">
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </div>
        
      </div>
    </div>
  );
}
