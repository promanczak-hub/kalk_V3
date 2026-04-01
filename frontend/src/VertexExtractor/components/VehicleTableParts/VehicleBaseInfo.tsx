import React, { useState, useCallback, useMemo } from "react";
import { ChevronUp, ChevronDown, Check, AlertTriangle, Copy, CheckCheck, Edit3, Car, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { SamarCategoryDropdown } from "./SamarCategoryDropdown";
import { EngineCategoryDropdown } from "./EngineCategoryDropdown";
import type { FleetVehicleView } from "../../types";
import type { DiscountAlert } from "../../hooks/useDiscountAlerts";
import { ServiceCostMeter } from "./ServiceCostMeter";

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
  mappedData?: MappedData | null;
  isExpanded: boolean;
  onToggleExpand: () => void;
  activeFinalPriceNet: number;
  totalCatalogPriceNet: number;
  formatCalculatedPrice: (val: number) => string;
  samarCandidates?: SamarCandidate[];
  onSamarCategoryChange?: (newCategory: string) => void;
  allSamarClasses?: string[];
  engineCandidates?: EngineCandidate[];
  onEngineCategoryChange?: (newCategory: string) => void;
  allEngineTypes?: string[];
  driveType?: string;
  onDriveTypeChange?: (newDriveType: string) => void;
  bodyType?: string;
  onBodyTypeChange?: (newBodyType: string) => void;
  bodyTypeOptions?: { name: string; vehicle_class: string }[];
  readinessResult?: {
    samar_class_id: number | null;
    fuel_type_id: number | null;
    status: "ready" | "partial" | "missing";
    body_match?: {
      matched: boolean;
      body_type_id: number | null;
      raw_input: string;
      score: number;
      match_method: string;
      vehicle_class?: string;
    };
  } | null;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  onConfigurationCodeChange?: (newCode: string) => void;
  crossCardAlerts?: DiscountAlert[];
  onScrollToVehicle?: (vehicleId: string) => void;
  paramPreview?: {
    service: {
      found: boolean;
      rate_per_km: number;
      base_rate?: number;
      m_brand?: number;
      m_fuel?: number;
      m_drive?: number;
      m_gearbox?: number;
      total_multiplier?: number;
      type: string;
      power_band?: string;
    };
  } | null;
  discountMode?: "offer" | "suggested" | "custom";
  setDiscountMode?: (mode: "offer" | "suggested" | "custom") => void;
  customDiscountPctRaw?: string | number;
  setCustomDiscountPctRaw?: (val: string) => void;
  offerDiscountPercentage?: number;
  suggestedDiscountPct?: number;
}

function detectPowerBand(
vehicle: FleetVehicleView,
): string | null {
const synth = vehicle.synthesis_data as Record<string, unknown> | undefined;

if (synth) {
    const cardSummary = synth.card_summary as Record<string, unknown> | undefined;
    if (cardSummary && typeof cardSummary.power_range === "string") {
      const match = cardSummary.power_range.match(/(LOW|MID|HIGH)/i);
      if (match) return match[1].toUpperCase();
    }
    if ("power_range" in synth && typeof synth.power_range === "string") {
      const match = synth.power_range.match(/(LOW|MID|HIGH)/i);
      if (match) return match[1].toUpperCase();
    }
}

if (vehicle.powertrain) {
    const kmMatch = vehicle.powertrain.match(/(\d{2,3})\s*(KM|HP|PS)/i);
    if (kmMatch) {
      const hp = parseInt(kmMatch[1]);
      if (hp <= 130) return "LOW";
      if (hp <= 200) return "MID";
      return "HIGH";
    }
    const kwMatch = vehicle.powertrain.match(/(\d{2,3})\s*kW/i);
    if (kwMatch) {
      const hp = Math.round(parseInt(kwMatch[1]) * 1.36);
      if (hp <= 130) return "LOW";
      if (hp <= 200) return "MID";
      return "HIGH";
    }
}

return null;
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

/** Readiness badge - shows SAMAR data availability with hover tooltip */
function ReadinessBadge({ result }: { result: NonNullable<VehicleBaseInfoProps["readinessResult"]> }) {
  const STATUS_CONFIG = {
    ready:   { icon: CheckCircle,  color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", label: "Gotowe" },
    partial: { icon: AlertCircle,  color: "text-amber-600",   bg: "bg-amber-50",   border: "border-amber-200",   label: "Częściowe" },
    missing: { icon: XCircle,      color: "text-red-500",     bg: "bg-red-50",     border: "border-red-200",     label: "Brak danych" },
  };
  const cfg = STATUS_CONFIG[result.status];
  const IconComp = cfg.icon;

  return (
    <span className="relative group/rb">
      <span className={`inline-flex items-center gap-1 h-[26px] px-2.5 rounded border text-[11px] font-semibold cursor-default transition-colors ${cfg.color} ${cfg.bg} ${cfg.border}`}
        style={{ fontFamily: "'Geist Mono', monospace" }}>
        <IconComp className="w-3.5 h-3.5" />
        {cfg.label}
      </span>
      {/* Tooltip */}
      <div className="absolute z-50 bottom-full mb-1.5 left-0 min-w-[220px] bg-white border border-slate-200 rounded-lg shadow-xl p-3 text-xs hidden group-hover/rb:block">
        <p className="font-semibold text-slate-700 mb-1.5">Gotowość kalkulacyjna SAMAR</p>
        <div className="space-y-1 text-slate-600">
          <div className="flex justify-between">
            <span>Klasa SAMAR:</span>
            <span className={result.samar_class_id != null ? "text-emerald-600 font-medium" : "text-red-500"}>
              {result.samar_class_id != null ? `ID: ${result.samar_class_id}` : "Brak"}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Typ paliwa:</span>
            <span className={result.fuel_type_id != null ? "text-emerald-600 font-medium" : "text-red-500"}>
              {result.fuel_type_id != null ? `ID: ${result.fuel_type_id}` : "Brak"}
            </span>
          </div>
          {result.body_match && (
            <div className="mt-1.5 pt-1.5 border-t border-slate-100">
              <div className="flex justify-between">
                <span>Nadwozie:</span>
                {result.body_match.matched ? (
                  <span className="text-emerald-600 font-medium">
                    {result.body_match.score}% ({result.body_match.match_method})
                  </span>
                ) : (
                  <span className="text-red-500">"{result.body_match.raw_input}" – brak</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
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
  mappedData,
  isExpanded,
  onToggleExpand,
  activeFinalPriceNet,
  totalCatalogPriceNet,
  formatCalculatedPrice,
  samarCandidates = [],
  onSamarCategoryChange,
  allSamarClasses = [],
  engineCandidates = [],
  onEngineCategoryChange,
  allEngineTypes = [],
  driveType = "",
  onDriveTypeChange,
  bodyType = "",
  onBodyTypeChange,
  bodyTypeOptions = [],
  readinessResult,
  isSelected = false,
  onToggleSelect,
  crossCardAlerts = [],
  onScrollToVehicle,
  paramPreview,
  onConfigurationCodeChange,
  discountMode,
  setDiscountMode,
  customDiscountPctRaw,
  setCustomDiscountPctRaw,
  offerDiscountPercentage = 0,
  suggestedDiscountPct = 0,
}: VehicleBaseInfoProps) {
const powerBand = detectPowerBand(vehicle);

return (
    <div
      className="p-4 sm:p-5 cursor-pointer select-none"
      onClick={onToggleExpand}
    >
      <div className="flex flex-col gap-3">
        
        {/* ── RZĄD 1: Identyfikacja + Cena + Akcje ── */}
        <div className="flex items-center gap-3 justify-between">
          
          {/* Lewa strona: Checkbox + Data + Nazwa + Kody */}
          <div className="flex items-center gap-3 min-w-0 flex-grow">
            {onToggleSelect && (
              <div
                className="flex-shrink-0"
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

            <span className="text-xs text-slate-400 tabular-nums whitespace-nowrap hidden sm:inline" style={{ fontFamily: "'Geist Mono', monospace" }}>
              {format(new Date(vehicle.created_at), "dd.MM.yyyy")}
            </span>

            <div className="min-w-0">
              <div className="flex items-baseline gap-2 flex-wrap">
                <h3 className="text-sm font-semibold text-slate-900 truncate">
                  {vehicle.brand || "?"} {vehicle.model}
                </h3>
                {hasValue(vehicle.trim_level) && (
                  <span className="text-xs text-slate-500 font-medium">{vehicle.trim_level}</span>
                )}
              </div>
              <p className="text-xs text-slate-500 line-clamp-1" style={{ fontFamily: "'Geist Mono', monospace" }}>
                {hasValue(vehicle.powertrain) ? vehicle.powertrain : "Brak danych napędu"}
              </p>
            </div>
          </div>

          {/* Prawa strona: Cena + Readiness + Chevron */}
          <div className="flex items-center gap-4 flex-shrink-0">
            <div className="flex flex-col items-end">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold" style={{ fontFamily: "'Geist Mono', monospace" }}>
                {activeFinalPriceNet > 0 && activeFinalPriceNet !== totalCatalogPriceNet ? "SUMA CAŁKOWITA" : totalCatalogPriceNet > 0 ? "CENA KATALOGOWA" : ""}
              </span>
              {(activeFinalPriceNet > 0 || totalCatalogPriceNet > 0) ? (
                <>
                  <span className="text-lg font-bold text-slate-900 tabular-nums tracking-tight" style={{ fontFamily: "'Geist Mono', monospace" }}>
                    {formatCalculatedPrice(activeFinalPriceNet > 0 ? activeFinalPriceNet : totalCatalogPriceNet)}{" "}
                    <span className="text-xs font-semibold text-slate-500">PLN BRUTTO</span>
                  </span>
                  <span className="text-xs text-slate-400 tabular-nums mt-0.5" style={{ fontFamily: "'Geist Mono', monospace" }}>
                    {formatCalculatedPrice(Math.round((activeFinalPriceNet > 0 ? activeFinalPriceNet : totalCatalogPriceNet) / 1.23))} PLN NETTO
                  </span>
                </>
              ) : (
                <span className="text-sm text-slate-400" style={{ fontFamily: "'Geist Mono', monospace" }}>Brak wyceny</span>
              )}
            </div>

            <div className="text-slate-400 group-hover:text-blue-500 transition-colors bg-slate-50 group-hover:bg-blue-50 rounded-full p-1 border border-transparent group-hover:border-blue-100">
              {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </div>
          </div>
        </div>

        {/* ── RZĄD 2: Kody + Klasyfikacja SAMAR + Status ── */}
        <div className="space-y-1.5">

          {/* Linia A: Kody identyfikacyjne + rabat */}
          <div className="flex items-center gap-2 flex-wrap">
            {hasValue(vehicle.offer_number) && (
              <CodeTag>{vehicle.offer_number}</CodeTag>
            )}
            {onConfigurationCodeChange ? (
              <div className="flex items-center gap-1 border border-slate-300 bg-slate-100 px-2.5 py-0.5 rounded text-sm group/edit focus-within:ring-2 focus-within:ring-blue-400 focus-within:border-blue-400 transition-all">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">CONFIG</span>
                <input
                  type="text"
                  defaultValue={vehicle.configuration_code || ""}
                  onBlur={(e) => {
                    if (e.target.value !== vehicle.configuration_code) {
                      onConfigurationCodeChange(e.target.value);
                    }
                  }}
                  className="bg-transparent border-none outline-none text-slate-700 font-mono text-sm w-24 focus:w-40 transition-all"
                  style={{ fontFamily: "'Geist Mono', monospace" }}
                  placeholder="Kod konfiguracji..."
                />
                <Edit3 className="w-3 h-3 text-slate-400 opacity-0 group-hover/edit:opacity-100 transition-opacity" />
              </div>
            ) : hasValue(vehicle.configuration_code) && (
              <CodeTag>{vehicle.configuration_code}</CodeTag>
            )}

            {/* Separator + rabat po prawej */}
            <div className="flex items-center gap-2 ml-auto flex-shrink-0">{/* rabat przeniesiony niżej */}</div>
          </div>

          {/* Linia B: Klasyfikacja pojazdu + serwis + status */}
          <div className="flex items-center h-[26px] bg-slate-50 border border-slate-100 rounded overflow-hidden divide-x divide-slate-200 w-fit max-w-full">
            {/* SAMAR */}
            {mappedData?.samar_category && onSamarCategoryChange ? (
              <div className="h-full" onClick={(e) => e.stopPropagation()}>
                <SamarCategoryDropdown
                  currentCategory={mappedData.samar_category}
                  candidates={samarCandidates}
                  allSamarClasses={allSamarClasses}
                  onCategoryChange={onSamarCategoryChange}
                  connected={true}
                />
              </div>
            ) : mappedData?.samar_category ? (
              <Tag connected={true}>SAMAR: {mappedData.samar_category}</Tag>
            ) : null}

            {/* Silnik */}
            {mappedData?.engine_class && onEngineCategoryChange ? (
              <div className="h-full" onClick={(e) => e.stopPropagation()}>
                <EngineCategoryDropdown
                  currentCategory={mappedData.fuel}
                  candidates={engineCandidates}
                  allEngineTypes={allEngineTypes}
                  onCategoryChange={onEngineCategoryChange}
                  connected={true}
                />
              </div>
            ) : mappedData?.engine_class ? (
              <Tag connected={true}>SILNIK: {mappedData.fuel} / {mappedData.engine_class}</Tag>
            ) : null}

            {/* Serwis */}
            {(paramPreview?.service?.found || powerBand) && (
              <div className="h-full flex items-center" onClick={(e) => e.stopPropagation()}>
                <ServiceCostMeter
                  mode="flat"
                  totalMultiplier={paramPreview?.service?.total_multiplier || (powerBand === "HIGH" ? 1.25 : powerBand === "LOW" ? 0.75 : 1.0)}
                  multipliers={paramPreview?.service?.found ? {
                    brand: paramPreview.service.m_brand || 1.0,
                    fuel: paramPreview.service.m_fuel || 1.0,
                    drive: paramPreview.service.m_drive || 1.0,
                    gearbox: paramPreview.service.m_gearbox || 1.0
                  } : { brand: 1.0, fuel: 1.0, drive: 1.0, gearbox: 1.0 }}
                />
              </div>
            )}

            {/* Oś napędowa */}
            {(driveType || onDriveTypeChange) && (
              <div className="h-full" onClick={(e) => e.stopPropagation()}>
                <DriveTypeTag current={driveType} onChange={onDriveTypeChange} connected={true} />
              </div>
            )}

            {/* Nadwozie */}
            {(bodyType || onBodyTypeChange) && (
              <div className="h-full" onClick={(e) => e.stopPropagation()}>
                <BodyTypeTag
                  current={bodyType}
                  dbOptions={bodyTypeOptions}
                  onChange={onBodyTypeChange}
                  currentVehicleType={mappedData?.vehicle_type}
                  connected={true}
                />
              </div>
            )}

            {/* Gotowe / status */}
            {readinessResult && (
              <div className="h-full flex items-center" onClick={(e) => e.stopPropagation()}>
                <ReadinessBadge result={readinessResult} />
              </div>
            )}
          </div>
        </div>

        {/* ── RZĄD 3: Rabat + Alert ── */}
        <div className="flex items-center gap-2 flex-wrap">
          {discountMode ? (
            <div className="flex h-[26px] bg-slate-50 border border-slate-200 rounded text-[11px] font-medium text-slate-600 overflow-hidden divide-x divide-slate-200 shadow-sm">
              <button
                type="button"
                className={`px-2.5 flex items-center transition-colors hover:bg-slate-100 ${
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
                className={`px-2.5 flex items-center transition-colors hover:bg-slate-100 ${
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
                  discountMode === "custom" ? "bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold pl-2" : "px-2.5"
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
                      className="w-12 h-full bg-transparent text-right outline-none px-1 text-blue-900 font-mono text-[11px]"
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
              className="inline-flex items-center gap-1 border border-amber-300 bg-amber-50 px-2 py-1.5 rounded text-xs font-semibold text-amber-700 hover:bg-amber-100 hover:border-amber-400 transition-colors cursor-pointer animate-in fade-in duration-300"
              title={`Kliknij, aby przewinąć do oferty ${crossCardAlerts[0].siblingOfferNumber || "(brak nr)"}`}
              onClick={(e) => {
                e.stopPropagation();
                const targetId = crossCardAlerts[0].siblingVehicleId;
                if (onScrollToVehicle) onScrollToVehicle(targetId);
              }}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Lepszy rabat (+{crossCardAlerts[0].deltaPp} pp.)
            </button>
          )}
        </div>

      </div>
    </div>
);
}
