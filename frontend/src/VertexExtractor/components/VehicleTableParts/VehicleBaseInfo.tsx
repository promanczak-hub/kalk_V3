import { ChevronUp, ChevronDown, Check, AlertTriangle } from "lucide-react";
import { format } from "date-fns";
import type { FleetVehicleView } from "../../types";
import { PriceDualFormat } from "./PriceDualFormat";
import { SamarCategoryDropdown } from "./SamarCategoryDropdown";
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
}

interface SamarCandidate {
  klasa: string;
  confidence: number;
}

interface VehicleBaseInfoProps {
  vehicle: FleetVehicleView;
  mappedData?: MappedData | null;
  isExpanded: boolean;
  onToggleExpand: () => void;
  activeFinalPrice: number;
  totalCatalogPrice: number;
  formatCalculatedPrice: (val: number) => string;
  samarCandidates?: SamarCandidate[];
  onSamarCategoryChange?: (newCategory: string) => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  crossCardAlerts?: DiscountAlert[];
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

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center border border-slate-200 bg-slate-50 px-2 py-0.5 rounded text-xs font-medium text-slate-600">
      {children}
    </span>
  );
}

export function VehicleBaseInfo({
  vehicle,
  mappedData,
  isExpanded,
  onToggleExpand,
  activeFinalPrice,
  totalCatalogPrice,
  formatCalculatedPrice,
  samarCandidates = [],
  onSamarCategoryChange,
  isSelected = false,
  onToggleSelect,
  crossCardAlerts = [],
}: VehicleBaseInfoProps) {
  const powerBand = detectPowerBand(vehicle);

  return (
    <div
      className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-start gap-4 cursor-pointer select-none"
      onClick={onToggleExpand}
    >
      {/* Selection checkbox */}
      {onToggleSelect && (
        <div
          className="flex-shrink-0 pt-0.5"
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
      {/* Date & Meta */}
      <div className="flex-shrink-0 w-full sm:w-36 flex flex-col gap-1 pt-0.5">
        <span className="text-xs text-slate-500 tabular-nums">
          {format(new Date(vehicle.created_at), "dd.MM.yyyy")}
        </span>
        <div className="flex gap-1.5 items-center flex-wrap">
          {hasValue(vehicle.offer_number) && (
            <Tag>{vehicle.offer_number}</Tag>
          )}
          {hasValue(vehicle.configuration_code) && (
            <Tag>{vehicle.configuration_code}</Tag>
          )}
        </div>
      </div>

      {/* Vehicle Identity */}
      <div className="flex-grow flex flex-col min-w-0 overflow-hidden">
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
              {mappedData.vehicle_type} · {mappedData.fuel} · {mappedData.transmission}
            </span>
          )}
        </div>

        <p className="text-xs text-slate-600 line-clamp-1 mt-0.5">
          {hasValue(vehicle.powertrain)
            ? vehicle.powertrain
            : "Brak danych napędu"}
        </p>

        {/* Metadata tags — all monochrome */}
        <div className="flex gap-2 mt-1.5 flex-wrap items-center">
          {vehicle.suggested_discount_pct != null && (
            <Tag>Rabat: {vehicle.suggested_discount_pct}%</Tag>
          )}
          {vehicle.synthesis_data && vehicle.suggested_discount_pct == null && (
            <Tag>Brak rabatu</Tag>
          )}
          {mappedData?.samar_category && onSamarCategoryChange ? (
            <SamarCategoryDropdown
              currentCategory={mappedData.samar_category}
              candidates={samarCandidates}
              onCategoryChange={onSamarCategoryChange}
            />
          ) : mappedData?.samar_category ? (
            <Tag>SAMAR: {mappedData.samar_category}</Tag>
          ) : null}
          {mappedData?.engine_class && (
            <Tag>{mappedData.fuel} / {mappedData.engine_class}</Tag>
          )}
          {powerBand && <Tag>Serwis: {powerBand}</Tag>}
          {crossCardAlerts.length > 0 && (
            <span
              className="inline-flex items-center gap-1 border border-amber-300 bg-amber-50 px-2 py-0.5 rounded text-xs font-semibold text-amber-700 animate-in fade-in duration-300"
              title={`Inna oferta (${crossCardAlerts[0].siblingOfferNumber || "brak nr"}) ma rabat ${crossCardAlerts[0].siblingDiscountPct}% vs ${crossCardAlerts[0].currentDiscountPct}%`}
            >
              <AlertTriangle className="w-3 h-3" />
              Lepszy rabat (+{crossCardAlerts[0].deltaPp} pp.)
            </span>
          )}
        </div>
      </div>

      {/* Price */}
      <div className="flex-shrink-0 text-right min-w-[180px] flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-start pt-0.5">
        <div className="flex flex-col items-end">
          {activeFinalPrice > 0 && activeFinalPrice !== totalCatalogPrice ? (
            <>
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-0.5">
                Suma Całkowita
              </span>
              <span className="text-lg font-semibold tracking-tight text-slate-900 tabular-nums">
                <PriceDualFormat
                  priceStr={formatCalculatedPrice(activeFinalPrice)}
                  align="right"
                />
              </span>
            </>
          ) : vehicle.base_price && vehicle.base_price !== "Brak" ? (
            <>
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-0.5">
                Cena Katalogowa
              </span>
              <span className="text-lg font-semibold tracking-tight text-slate-800 tabular-nums">
                <PriceDualFormat priceStr={vehicle.base_price} align="right" />
              </span>
            </>
          ) : (
            <span className="text-sm text-slate-500 mt-2">Brak wyceny</span>
          )}
        </div>

        <button className="sm:ml-4 sm:hidden ml-auto p-1 text-slate-400 hover:text-slate-600">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
      </div>

      <div className="hidden sm:flex items-center pl-4 text-slate-300 group-hover:text-slate-500 transition-colors">
        {isExpanded ? (
          <ChevronUp className="w-5 h-5" />
        ) : (
          <ChevronDown className="w-5 h-5" />
        )}
      </div>
    </div>
  );
}
