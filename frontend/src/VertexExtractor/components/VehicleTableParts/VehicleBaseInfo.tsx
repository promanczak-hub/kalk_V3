import React, { useState, useCallback, useRef, useMemo } from "react";
import { ChevronUp, ChevronDown, Check, AlertTriangle, Copy, CheckCheck, CheckCircle, XCircle, AlertCircle, Edit3 } from "lucide-react";
import { Autocomplete, TextField } from "@mui/material";
import type { AutocompleteRenderInputParams } from "@mui/material";
import { format } from "date-fns";
import type { FleetVehicleView } from "../../types";
import { PriceDualFormat } from "./PriceDualFormat";
import { SamarCategoryDropdown } from "./SamarCategoryDropdown";
import { EngineCategoryDropdown } from "./EngineCategoryDropdown";
import { VehicleTypeDropdown } from "./VehicleTypeDropdown";
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

interface SamarCandidate {
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
onVehicleTypeChange?: (newType: string) => void;
/** DB body_types — single source of truth for dropdown options */
bodyTypeOptions?: { name: string; vehicle_class: string }[];
isSelected?: boolean;
onToggleSelect?: () => void;
onConfigurationCodeChange?: (newCode: string) => void;
crossCardAlerts?: DiscountAlert[];
onScrollToVehicle?: (vehicleId: string) => void;
readinessResult?: {
    overall_status: "ready" | "partial" | "not_ready";
    samar_class_id: number | null;
    fuel_type_id: number | null;
    checks: { param: string; status: string; value: string }[];
    critical_count: number;
    warning_count: number;
    resolve_error?: string;
    body_match?: {
      matched_name: string | null;
      vehicle_class: string | null;
      score: number;
      match_method: string;
      raw_input: string;
    };
  } | null;
  paramPreview?: {
    service: {
      found: boolean;
      rate_per_km: number;
      base_rate: number;
      m_brand: number;
      m_fuel: number;
      m_drive: number;
      m_gearbox: number;
      total_multiplier: number;
      type: string;
    };
  } | null;
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

function Tag({ children, connected }: { children: React.ReactNode; connected?: boolean }) {
return (
    <span
      className={`inline-flex items-center font-medium text-slate-600 ${connected ? "justify-center h-full px-2.5 py-1 text-[11px] bg-slate-50/50" : "bg-slate-50 px-2 py-1 text-xs border border-slate-200 rounded"}`}
      style={{ fontFamily: "'Geist Mono', monospace", lineHeight: 1 }}
    >
      {children}
    </span>
);
}

const DRIVE_TYPE_OPTIONS = [
{ value: "4x2 (FWD)", label: "4x2 (FWD)" },
{ value: "4x2 (RWD)", label: "4x2 (RWD)" },
{ value: "4x4 (AWD)", label: "4x4 (AWD)" },
];

function DriveTypeTag({ current, onChange, connected }: { current: string; onChange?: (v: string) => void; connected?: boolean }) {
if (!onChange) {
    return current ? <Tag connected={connected}>Oś: {current}</Tag> : null;
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

function BodyTypeTag({ current, dbOptions, onChange, connected, currentVehicleType }: {
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
      const isCommercial = currentVehicleType.toLowerCase().includes("commercial") || 
                           currentVehicleType.toLowerCase().includes("dostawcz");
      filtered = dbOptions.filter(o => {
        const oClass = (o.vehicle_class || "").toLowerCase();
        if (isCommercial) return oClass.includes("commercial") || oClass.includes("dostawcz");
        return oClass.includes("passenger") || oClass.includes("osobow");
      });
      if (filtered.length === 0) filtered = dbOptions;
    }
    return Array.from(new Set(filtered.map(o => o.name))).sort();
  }, [dbOptions, currentVehicleType]);

  if (!onChange) {
    return current ? <Tag connected={connected}>Nadwozie: {normValue}</Tag> : null;
  }

  return (
    <div className="flex items-center h-full">
      <Autocomplete
        size="small"
        options={options}
        value={normValue || null}
        onChange={(_: React.SyntheticEvent, newValue: string | null) => {
          if (newValue) onChange(newValue);
        }}
        freeSolo
        renderInput={(params: AutocompleteRenderInputParams) => (
          <TextField
            {...params}
            placeholder="Nadwozie..."
            variant="standard"
            InputProps={{
              ...params.InputProps,
              disableUnderline: true,
              style: { 
                fontSize: '11px', 
                fontFamily: "'Geist Mono', monospace",
                padding: '0 10px',
                height: '24px',
                color: '#475569'
              }
            }}
            sx={{
              width: 140,
              backgroundColor: 'transparent',
              '& .MuiInputBase-root': { height: '100%' }
            }}
          />
        )}
        sx={{
          '& .MuiAutocomplete-endAdornment': { display: 'none' }
        }}
      />
    </div>
  );
}

/** Readiness badge - shows SAMAR data availability with hover tooltip */
function ReadinessBadge({ result }: { result: NonNullable<VehicleBaseInfoProps["readinessResult"]> }) {
const [showTooltip, setShowTooltip] = useState(false);
const tooltipRef = useRef<HTMLDivElement>(null);

const statusConfig = {
    ready:     { icon: CheckCircle,  color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", label: "Gotowe" },
    partial:   { icon: AlertCircle,  color: "text-amber-600",   bg: "bg-amber-50",   border: "border-amber-200",   label: "Częściowo" },
    not_ready: { icon: XCircle,      color: "text-red-600",     bg: "bg-red-50",     border: "border-red-200",     label: "Brak danych" },
};

const cfg = statusConfig[result.overall_status];
const Icon = cfg.icon;

return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onClick={(e) => e.stopPropagation()}
    >
      <span
        className={`inline-flex items-center gap-1 border ${cfg.border} ${cfg.bg} px-2 py-1 rounded text-xs font-medium ${cfg.color} cursor-default`}
        style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.95rem", lineHeight: 1 }}
      >
        <Icon className="w-3.5 h-3.5" />
        {cfg.label}
      </span>

      {showTooltip && (
        <div
          ref={tooltipRef}
          className="absolute left-0 top-full mt-1 z-50 w-72 bg-white rounded-lg shadow-xl border border-slate-200 p-3 animate-in fade-in slide-in-from-top-1 duration-150"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
            Gotowość kalkulacyjna SAMAR
          </div>
          {result.resolve_error && (
            <div className="text-xs text-red-600 font-medium mb-2 p-1.5 bg-red-50 rounded border border-red-100">
              {result.resolve_error}
            </div>
          )}
          {result.checks.length > 0 && (
            <div className="space-y-1">
              {result.checks.map((check, i) => {
                const icon = check.status === "ok" ? "OK" : check.status === "warn" ? "WARN" : "ERR";
                return (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-slate-700">
                      {icon} {check.param}
                    </span>
                    <span className={`font-mono text-[10px] ${
                      check.status === "ok" ? "text-emerald-600" : check.status === "warn" ? "text-amber-600" : "text-red-600"
                    }`}>
                      {check.value}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
          {/* Body type match info */}
          {result.body_match && result.body_match.raw_input && (
            <div className="mt-2 pt-1.5 border-t border-slate-100">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                Dopasowanie nadwozia
              </div>
              {result.body_match.score > 0 ? (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-700">
                    {result.body_match.raw_input} → {result.body_match.matched_name}
                  </span>
                  <span className={`font-mono text-[10px] ${
                    result.body_match.score >= 90 ? "text-emerald-600" : "text-amber-600"
                  }`}>
                    {result.body_match.score}% ({result.body_match.match_method})
                  </span>
                </div>
              ) : (
                <div className="text-xs text-red-600 font-medium p-1.5 bg-red-50 rounded border border-red-100">
                  Uwaga: "{result.body_match.raw_input}" - brak dopasowania.
                  Korekta WR za nadwozie = 0%
                </div>
              )}
              {result.body_match.vehicle_class && (
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Klasa: {result.body_match.vehicle_class}
                </div>
              )}
            </div>
          )}
          {result.samar_class_id != null && (
            <div className="mt-2 pt-1.5 border-t border-slate-100 text-[10px] text-slate-400">
              SAMAR ID: {result.samar_class_id} · Fuel ID: {result.fuel_type_id}
            </div>
          )}
        </div>
      )}
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
onVehicleTypeChange,
bodyTypeOptions = [],

isSelected = false,
onToggleSelect,
crossCardAlerts = [],
onScrollToVehicle,
readinessResult,
paramPreview,
onConfigurationCodeChange,
}: VehicleBaseInfoProps) {
const powerBand = detectPowerBand(vehicle);

return (
    <div
      className="p-4 sm:p-5 cursor-pointer select-none"
      onClick={onToggleExpand}
    >
      {/* Row 1: Checkbox + Date + Vehicle Name + Price + Chevron */}
      <div className="flex items-start gap-3">
        {/* Selection checkbox */}
        {onToggleSelect && (
          <div
            className="flex-shrink-0 pt-1"
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

        {/* Date */}
        <div className="flex-shrink-0 pt-0.5">
          <span className="text-xs text-slate-500 tabular-nums whitespace-nowrap">
            {format(new Date(vehicle.created_at), "dd.MM.yyyy")}
          </span>
        </div>

        {/* Vehicle Identity - grows to fill */}
        <div className="flex-grow min-w-0 overflow-hidden">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-slate-900 truncate">
              {vehicle.brand || "?"} {vehicle.model}
            </h3>
            {hasValue(vehicle.trim_level) && (
              <span className="text-xs text-slate-500 font-medium">{vehicle.trim_level}</span>
            )}
            {mappedData && (
              <span
                className="text-xs text-slate-500 hidden sm:inline-block"
                title="Klasyfikacja AI"
              >
                {mappedData.fuel} · {mappedData.transmission}
              </span>
            )}

          </div>

          <p className="text-xs text-slate-600 line-clamp-1 mt-0.5">
            {hasValue(vehicle.powertrain)
              ? vehicle.powertrain
              : "Brak danych napędu"}
          </p>
        </div>

        {/* Price */}
        <div className="flex-shrink-0 text-right min-w-[160px] flex flex-col items-end pt-0.5">
          {activeFinalPriceNet > 0 && activeFinalPriceNet !== totalCatalogPriceNet ? (
            <>
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-0.5">
                Suma Całkowita
              </span>
              <span className="text-lg font-semibold tracking-tight text-slate-900 tabular-nums">
                <PriceDualFormat
                  priceStr={formatCalculatedPrice(activeFinalPriceNet)}
                  align="right"
                />
              </span>
            </>
          ) : totalCatalogPriceNet > 0 ? (
            <>
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-0.5">
                Cena Katalogowa
              </span>
              <span className="text-lg font-semibold tracking-tight text-slate-800 tabular-nums">
                <PriceDualFormat priceStr={formatCalculatedPrice(totalCatalogPriceNet)} align="right" />
              </span>
            </>
          ) : (
            <span className="text-sm text-slate-500 mt-2">Brak wyceny</span>
          )}
        </div>

        {/* Chevron */}
        <div className="hidden sm:flex items-center pl-2 text-slate-300 group-hover:text-slate-500 transition-colors pt-1">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </div>

        {/* Mobile chevron */}
        <button className="sm:hidden p-1 text-slate-400 hover:text-slate-600 flex-shrink-0">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Row 2: Badges — two dedicated lines for stable alignment */}
      <div className="mt-2 ml-0 sm:ml-8 space-y-1.5">
        {/* Line A: Kody identyfikacyjne + rabat */}
        <div className="flex items-center gap-2 flex-wrap">
          {hasValue(vehicle.offer_number) && (
            <CodeTag>{vehicle.offer_number}</CodeTag>
          )}
          {onConfigurationCodeChange ? (
            <div className="flex items-center gap-1 border border-slate-300 bg-slate-100 px-2.5 py-0.5 rounded text-sm group focus-within:ring-2 focus-within:ring-blue-400 focus-within:border-blue-400 transition-all">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">CONFIG</span>
              <input
                type="text"
                defaultValue={vehicle.configuration_code || ""}
                onBlur={(e) => {
                  if (e.target.value !== vehicle.configuration_code) {
                    onConfigurationCodeChange(e.target.value);
                  }
                }}
                className="bg-transparent border-none outline-none text-slate-700 font-mono text-sm w-32 focus:w-48 transition-all"
                style={{ fontFamily: "'Geist Mono', monospace" }}
                placeholder="Kod konfiguracji..."
              />
              <Edit3 className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          ) : hasValue(vehicle.configuration_code) && (
            <CodeTag>{vehicle.configuration_code}</CodeTag>
          )}
          {vehicle.suggested_discount_pct != null ? (
            <Tag>Rabat: {vehicle.suggested_discount_pct}%</Tag>
          ) : vehicle.synthesis_data ? (
            <Tag>Brak rabatu</Tag>
          ) : null}
        </div>

        {/* Line B: Klasyfikacja + serwis + status — zawsze od lewej krawędzi */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-stretch border border-slate-200 rounded-md bg-white divide-x divide-slate-200 shadow-sm h-[26px]">
            {mappedData?.samar_category && onSamarCategoryChange ? (
              <SamarCategoryDropdown
                currentCategory={mappedData.samar_category}
                candidates={samarCandidates}
                allSamarClasses={allSamarClasses}
                onCategoryChange={onSamarCategoryChange}
                connected={true}
              />
            ) : mappedData?.samar_category ? (
              <Tag connected={true}>SAMAR: {mappedData.samar_category}</Tag>
            ) : null}
            {mappedData?.engine_class && onEngineCategoryChange ? (
              <EngineCategoryDropdown
                currentCategory={mappedData.fuel}
                candidates={engineCandidates}
                allEngineTypes={allEngineTypes}
                onCategoryChange={onEngineCategoryChange}
                connected={true}
              />
            ) : mappedData?.engine_class ? (
              <Tag connected={true}>{mappedData.fuel} / {mappedData.engine_class}</Tag>
            ) : null}
            {(paramPreview?.service?.found || powerBand) && (
              <div className="flex items-center px-3 bg-slate-50/50 h-full">
                <ServiceCostMeter 
                  mode="flat" 
                  totalMultiplier={paramPreview?.service?.total_multiplier || (powerBand === "HIGH" ? 1.25 : powerBand === "LOW" ? 0.75 : 1.0)}
                  multipliers={paramPreview?.service?.found ? {
                    brand: paramPreview.service.m_brand,
                    fuel: paramPreview.service.m_fuel,
                    drive: paramPreview.service.m_drive,
                    gearbox: paramPreview.service.m_gearbox
                  } : {
                    brand: 1.0,
                    fuel: 1.0,
                    drive: 1.0,
                    gearbox: 1.0
                  }}
                />
              </div>
            )}
            <DriveTypeTag current={driveType} onChange={onDriveTypeChange} connected={true} />
            {onVehicleTypeChange && (
              <VehicleTypeDropdown
                currentType={mappedData?.vehicle_type || ""}
                onTypeChange={onVehicleTypeChange}
                connected={true}
              />
            )}
            <BodyTypeTag
              current={bodyType}
              dbOptions={bodyTypeOptions}
              onChange={onBodyTypeChange}
              currentVehicleType={mappedData?.vehicle_type}
              connected={true}
            />
          </div>

          {readinessResult && <ReadinessBadge result={readinessResult} />}
          {crossCardAlerts.length > 0 && (
            <button
              type="button"
              className="inline-flex items-center gap-1 border border-amber-300 bg-amber-50 px-2 py-1 rounded text-xs font-semibold text-amber-700 hover:bg-amber-100 hover:border-amber-400 transition-colors cursor-pointer animate-in fade-in duration-300"
              title={`Kliknij, aby przewinąć do oferty ${crossCardAlerts[0].siblingOfferNumber || "(brak nr)"} z rabatem ${crossCardAlerts[0].siblingDiscountPct}%`}
              onClick={(e) => {
                e.stopPropagation();
                const targetId = crossCardAlerts[0].siblingVehicleId;
                if (onScrollToVehicle) {
                  onScrollToVehicle(targetId);
                } else {
                  const el = document.querySelector(`[data-vehicle-id="${targetId}"]`);
                  if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "center" });
                    el.classList.add("ring-4", "ring-amber-300");
                    setTimeout(() => el.classList.remove("ring-4", "ring-amber-300"), 2000);
                  }
                }
              }}
            >
              <AlertTriangle className="w-3 h-3" />
              Lepszy rabat (+{crossCardAlerts[0].deltaPp} pp.) →
            </button>
          )}
        </div>
      </div>
    </div>
);
}
