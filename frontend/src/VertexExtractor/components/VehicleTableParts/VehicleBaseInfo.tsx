import { Calendar, Tag, Car, ChevronUp, ChevronDown } from "lucide-react";
import { format } from "date-fns";
import type { FleetVehicleView } from "../../types";
import { PriceDualFormat } from "./PriceDualFormat"; // We will probably extract this out later too, or assume it's moved

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

interface VehicleBaseInfoProps {
  vehicle: FleetVehicleView;
  mappedData?: MappedData | null;
  isExpanded: boolean;
  onToggleExpand: () => void;
  activeFinalPrice: number;
  totalCatalogPrice: number;
  formatCalculatedPrice: (val: number) => string;
}

export function VehicleBaseInfo({
  vehicle,
  mappedData,
  isExpanded,
  onToggleExpand,
  activeFinalPrice,
  totalCatalogPrice,
  formatCalculatedPrice,
}: VehicleBaseInfoProps) {
  
  const renderCostCategoryBadge = () => {
    let powerBand = null;
    const synth = vehicle.synthesis_data as Record<string, unknown> | undefined;
    
    // Check card_summary.power_range first (correct nesting)
    if (synth) {
      const cardSummary = synth.card_summary as Record<string, unknown> | undefined;
      if (cardSummary && typeof cardSummary.power_range === 'string') {
        const match = cardSummary.power_range.match(/(LOW|MID|HIGH)/i);
        if (match) powerBand = match[1].toUpperCase();
      }
      // Fallback to top-level (legacy)
      if (!powerBand && "power_range" in synth && typeof synth.power_range === 'string') {
        const match = synth.power_range.match(/(LOW|MID|HIGH)/i);
        if (match) powerBand = match[1].toUpperCase();
      }
    }
    
    if (!powerBand && vehicle.powertrain) {
      // Match KM/HP
      const kmMatch = vehicle.powertrain.match(/(\d{2,3})\s*(KM|HP|PS)/i);
      if (kmMatch) {
        const hp = parseInt(kmMatch[1]);
        if (hp <= 130) powerBand = "LOW";
        else if (hp <= 200) powerBand = "MID";
        else powerBand = "HIGH";
      } else {
        // Match kW and convert (1 kW ≈ 1.36 KM)
        const kwMatch = vehicle.powertrain.match(/(\d{2,3})\s*kW/i);
        if (kwMatch) {
          const hp = Math.round(parseInt(kwMatch[1]) * 1.36);
          if (hp <= 130) powerBand = "LOW";
          else if (hp <= 200) powerBand = "MID";
          else powerBand = "HIGH";
        }
      }
    }
    
    if (!powerBand) return null;

    let bgColor = "bg-slate-50 border-slate-200 text-slate-700";
    if (powerBand === "LOW") bgColor = "bg-emerald-50 border-emerald-100 text-emerald-700";
    else if (powerBand === "MID") bgColor = "bg-amber-50 border-amber-100 text-amber-700";
    else if (powerBand === "HIGH") bgColor = "bg-rose-50 border-rose-100 text-rose-700";

    return (
      <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-medium ${bgColor}`}>
        Koszty Serwisowe: {powerBand}
      </span>
    );
  };

  return (
    <div
      className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4 cursor-pointer select-none"
      onClick={onToggleExpand}
    >
      {/* Date & Meta */}
      <div className="flex-shrink-0 w-full sm:w-32 flex flex-col">
        <div className="flex items-center text-slate-500 text-xs mb-1">
          <Calendar className="w-3 h-3 mr-1" />
          {format(new Date(vehicle.created_at), "dd.MM.yyyy")}
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          {vehicle.offer_number && vehicle.offer_number !== "Brak" && vehicle.offer_number !== "-" ? (
             <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
               <Tag className="w-2.5 h-2.5 mr-1" />
               {vehicle.offer_number}
             </span>
          ) : null}
          {vehicle.configuration_code && vehicle.configuration_code !== "Brak" && vehicle.configuration_code !== "-" ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-50 text-indigo-700">
              <Car className="w-2.5 h-2.5 mr-1" />
              {vehicle.configuration_code}
            </span>
          ) : null}
        </div>
      </div>

      {/* Vehicle Identity */}
      <div className="flex-grow flex flex-col min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-900 truncate flex items-center gap-2 flex-wrap">
            <span>{vehicle.brand || "?"} {vehicle.model}</span>
            {mappedData && (
              <span 
                className="text-xs font-normal text-slate-500 opacity-90 ml-2 hidden sm:inline-block"
                title="Wykryto automatycznie przez AI wg katalogu cyfrowego bliźniaka"
              >
                ({mappedData.brand} / {mappedData.model} / {mappedData.trim_level} / {mappedData.transmission} / {mappedData.fuel} / {mappedData.vehicle_type})
              </span>
            )}
          </h3>
          {vehicle.suggested_discount_pct != null && (
            <span 
              className="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-700/10 shadow-sm whitespace-nowrap cursor-help"
              title={vehicle.suggested_discount_source || "Wykryto sugerowany rabat na podstawie konfiguracji pojazdu."}
            >
              ✨ Sugerowany Rabat: {vehicle.suggested_discount_pct}%
            </span>
          )}
          {vehicle.synthesis_data && vehicle.suggested_discount_pct == null && (
            <span className="inline-flex items-center rounded-md bg-slate-50 px-2 py-1 text-xs font-medium text-slate-500 ring-1 ring-inset ring-slate-500/10 shadow-sm whitespace-nowrap">
              🚫 Brak rabatu flotowego
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
          {vehicle.powertrain && vehicle.powertrain !== "Brak" ? vehicle.powertrain : "Brak danych napędu"}
        </p>
        <div className="flex gap-2 mt-1.5 flex-wrap">
          {mappedData?.samar_category && (
            <span className="inline-flex items-center rounded-sm bg-blue-50 border border-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
              Klasa SAMAR: {mappedData.samar_category}
            </span>
          )}
          {mappedData?.engine_class && (
            <span className="inline-flex items-center rounded-sm bg-teal-50 border border-teal-100 px-2 py-0.5 text-[10px] font-medium text-teal-700">
              Silnik/Napęd: {mappedData.fuel} / {mappedData.engine_class}
            </span>
          )}
          {renderCostCategoryBadge()}
          {vehicle.emissions && vehicle.emissions !== "Brak" && vehicle.emissions !== "-" && (
            <span className="inline-flex items-center rounded-full bg-slate-50 border border-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
              WLTP: {vehicle.emissions}
            </span>
          )}
          {vehicle.wheels && vehicle.wheels !== "Brak" && (
              <span className="inline-flex items-center rounded-full bg-slate-50 border border-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
                Koła: {vehicle.wheels}
              </span>
          )}
        </div>
      </div>

      {/* Highlighted Price */}
      <div className="flex-shrink-0 text-right min-w-[140px] flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center">
        
        <div className="flex flex-col items-end">
           {activeFinalPrice > 0 && activeFinalPrice !== totalCatalogPrice ? (
             <>
               <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-0.5">
                 Suma Całkowita
               </div>
               <div className="text-lg font-bold tracking-tight text-blue-600">
                 <PriceDualFormat priceStr={formatCalculatedPrice(activeFinalPrice)} align="right" />
               </div>
             </>
           ) : vehicle.base_price && vehicle.base_price !== "Brak" ? (
              <>
               <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-0.5">
                 Cena Katalogowa
               </div>
               <div className="text-lg font-bold tracking-tight text-slate-800">
                 <PriceDualFormat priceStr={vehicle.base_price} align="right" />
               </div>
              </>
           ) : (
              <div className="text-sm font-medium text-slate-400 mt-2">Brak wyceny</div>
           )}
        </div>

        <button className="sm:ml-4 sm:hidden ml-auto p-1 text-slate-400 hover:text-slate-600">
           {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      <div className="hidden sm:flex items-center pl-4 text-slate-300 group-hover:text-blue-500 transition-colors">
        {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
      </div>
    </div>
  );
}
