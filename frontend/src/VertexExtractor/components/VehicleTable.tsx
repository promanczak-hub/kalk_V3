import { useState, useEffect } from "react";
import {
  Database,
  ExternalLink,
  Loader2,
  RefreshCw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Car,
  Calendar,
  Tag,
  Info,
  Banknote,
  CheckCircle2,
  Wand2
} from "lucide-react";
import { format } from "date-fns";
import type { FleetVehicleView } from "../types";
import { cn } from "./ui/DocumentCard";

import { DocumentViewerModal } from "./DocumentViewerModal";

const parsePriceToNumber = (priceStr?: string | null): number => {
  if (!priceStr || priceStr === "Brak") return 0;
  
  let str = priceStr.replace(/\s+/g, "").replace(/[^\d.,-]/g, "");
  if (!str) return 0;

  const hasComma = str.includes(",");
  const hasDot = str.includes(".");
  
  if (hasComma && hasDot) {
    if (str.lastIndexOf(",") > str.lastIndexOf(".")) {
      str = str.replace(/\./g, "").replace(",", ".");
    } else {
      str = str.replace(/,/g, "");
    }
  } else if (hasComma) {
    const parts = str.split(",");
    if (parts.length === 2 && parts[1].length === 3) {
      str = str.replace(",", "");
    } else {
      str = str.replace(",", ".");
    }
  } else if (hasDot) {
    const parts = str.split(".");
    if (parts[parts.length - 1].length === 3) {
      str = str.replace(/\./g, "");
    }
  }
  
  const num = parseFloat(str);
  return isNaN(num) ? 0 : num;
};

// --- Helper Component to display Netto & Brutto ---
function PriceDualFormat({
  priceStr,
  align = "right",
  className = "",
  inline = false,
}: {
  priceStr?: string | null;
  align?: "left" | "center" | "right";
  className?: string;
  inline?: boolean;
}) {
  if (!priceStr || priceStr === "Brak") {
    return <span className="text-slate-400 font-normal text-sm">Brak</span>;
  }

  const cleaned = priceStr.toLowerCase();
  const value = parsePriceToNumber(priceStr);
  if (value === 0) return <span>{priceStr}</span>;

  const formatCurrency = (val: number) =>
    val
      .toLocaleString("pl-PL", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      })
      .replace(",", ".") + " PLN";

  // If we have a non-zero value, format it into Dual Format.
  // Default to Brutto if "netto" is not explicitly specified in the string.
  const isNetto = cleaned.includes("netto");
  const netto = isNetto ? value : value / 1.23;
  const brutto = isNetto ? value * 1.23 : value;

  if (inline) {
    return (
       <span className={className}>
         {formatCurrency(brutto)} <span className="text-[0.9em]">brutto</span> /{" "}
         <span className="opacity-60">{formatCurrency(netto)} <span className="text-[0.9em]">netto</span></span>
       </span>
    );
  }

  const alignClass =
    align === "left"
      ? "items-start"
      : align === "center"
      ? "items-center"
      : "items-end";

  return (
    <div className={cn("flex flex-col", alignClass, className)}>
      <span className="flex items-baseline gap-1">
        {formatCurrency(brutto)}
        <span className="text-[0.7em] font-medium opacity-70 uppercase tracking-wider">
          brutto
        </span>
      </span>
      <span className="text-[0.65em] opacity-60 font-semibold leading-none mt-1 uppercase tracking-wider">
        {formatCurrency(netto)} netto
      </span>
    </div>
  );
}

// --- Subcomponent for Individual Vehicle Row as a Card ---
function VehicleRowCard({
  vehicle,
  handleOpenSavedJson,
  onRefresh,
}: {
  vehicle: FleetVehicleView;
  handleOpenSavedJson: (id: string, titleName: string) => void;
  onRefresh: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [overridePrompt, setOverridePrompt] = useState("");
  const [isOverriding, setIsOverriding] = useState(false);

  const [isViewerOpen, setIsViewerOpen] = useState(false);

  interface MappedData {
    brand: string;
    model: string;
    fuel: string;
    vehicle_type: string;
    trim_level: string;
    transmission: string;
  }

  
  // Local mapped data state to store result for old documents
  const [localMappedData, setLocalMappedData] = useState<MappedData | null>(null);
  const [isMapping, setIsMapping] = useState(false);

  // Read mapped_data directly from synthesis_data (processed in the background backend job)
  const serverMappedData = vehicle.synthesis_data?.mapped_ai_data as MappedData | undefined;
  
  // Fallback to local state if missing from server
  const mappedData = localMappedData || serverMappedData;

  const handleMapDataSilent = async () => {
    if (!vehicle.synthesis_data) return;
    setIsMapping(true);
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/api/extract/map-vehicle-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_json: vehicle.synthesis_data,
        }),
      });

      if (!res.ok) {
        throw new Error("Błąd podczas wywołania API mapowania danych.");
      }

      const data = await res.json();
      setLocalMappedData(data);
    } catch (err) {
      console.error(err);
      // Suppress alert for silent mode
    } finally {
      setIsMapping(false);
    }
  };

  // Auto-map if expanded and data is missing
  useEffect(() => {
    if (isExpanded && vehicle.synthesis_data && !mappedData && !isMapping) {
      handleMapDataSilent();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded, mappedData, vehicle.synthesis_data]);

  // Helper to visually highlight user modifications
  const renderOptionName = (name: string) => {
    if (vehicle.verification_status === "processing") return name;
    
    const modKeyword = " (modyfikacja użytkownika)";
    if (name.includes(modKeyword)) {
      return (
        <span className="inline-flex items-center flex-wrap gap-1.5">
          <span>{name.replace(modKeyword, "")}</span>
          <span className="inline-flex items-center rounded-md bg-emerald-50 px-1.5 py-0.5 text-[9px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
            <Wand2 className="w-2.5 h-2.5 mr-1" />
            Modyfikacja użytkownika
          </span>
        </span>
      );
    }
    return name;
  };

  const handleManualOverride = async () => {
    if (!overridePrompt.trim()) return;
    setIsOverriding(true);
    try {
      // Dynamic import to avoid top-level issues if not needed yet
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

      // Call the Flash API Endpoint
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/api/extract/manual-override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_json: vehicle.synthesis_data,
          user_prompt: overridePrompt,
        }),
      });

      if (!res.ok) {
        throw new Error("Błąd z odpowiedzi serwera.");
      }

      const updatedJson = await res.json();

      // Overwrite DB
      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setIsOverrideModalOpen(false);
      setOverridePrompt("");
      onRefresh();
    } catch (err) {
      console.error(err);
      alert("Błąd podczas modyfikacji: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    } finally {
      setIsOverriding(false);
    }
  };


  const [discountMode, setDiscountMode] = useState<"offer" | "suggested" | "custom">("offer");
  const [customDiscountPctRaw, setCustomDiscountPctRaw] = useState<string | number>("");

  const customDiscountPct = Number(customDiscountPctRaw) || 0;

  const basePrice = parsePriceToNumber(vehicle.base_price);
  const optionsPrice = parsePriceToNumber(vehicle.options_price);
  const totalCatalogPrice = basePrice + optionsPrice;

  // 1. Discount from Offer (Parsed by AI)
  const offerFinalPrice = parsePriceToNumber(vehicle.final_price_pln);
  const hasOfferFinalPrice =
    vehicle.final_price_pln &&
    vehicle.final_price_pln !== "Brak" &&
    vehicle.final_price_pln !== vehicle.base_price;
  const isDealerOffer =
    hasOfferFinalPrice && offerFinalPrice > 0 && offerFinalPrice < totalCatalogPrice - 1.0;
  const offerDiscountPercentage =
    isDealerOffer && totalCatalogPrice > 0
      ? Math.round(((totalCatalogPrice - offerFinalPrice) / totalCatalogPrice) * 100)
      : 0;

  // 2. Discount from Suggested sources (e.g. Supabase)
  const suggestedDiscountPct = vehicle.suggested_discount_pct || 0;

  // Determine active values based on selected mode
  let activeDiscountPct = 0;
  let activeFinalPrice = totalCatalogPrice;

  if (discountMode === "offer" && isDealerOffer) {
    activeDiscountPct = offerDiscountPercentage;
    activeFinalPrice = offerFinalPrice;
  } else if (discountMode === "suggested") {
    activeDiscountPct = suggestedDiscountPct;
    activeFinalPrice = totalCatalogPrice * (1 - suggestedDiscountPct / 100);
  } else if (discountMode === "custom") {
    activeDiscountPct = customDiscountPct;
    activeFinalPrice = totalCatalogPrice * (1 - customDiscountPct / 100);
  }

  // Helper string formatting for the price display component
  const formatCalculatedPrice = (val: number) => {
      if (val === 0) return "Brak";
      const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
      return `${val.toFixed(2)} PLN ${isNetto ? 'netto' : 'brutto'}`;
  };

  const factoryOptions =
    vehicle.paid_options?.filter(
      (o) => o.category?.includes("Fabryczna") || !o.category,
    ) || [];
  const serviceOptions =
    vehicle.paid_options?.filter(
      (o) => o.category && !o.category.includes("Fabryczna"),
    ) || [];

  if (vehicle.exterior_color && vehicle.exterior_color !== "Brak") {
    const isAlreadyAdded = factoryOptions.some(
      (opt) =>
        opt.name.toLowerCase().includes("lakier") ||
        vehicle.exterior_color!.toLowerCase().includes(opt.name.toLowerCase()),
    );
    if (!isAlreadyAdded) {
      let name = `Lakier: ${vehicle.exterior_color}`;
      let price = "";
      const match =
        vehicle.exterior_color.match(
          /\((?:dopłata\s*)?([\d\s,.]+\s*(?:PLN|zł|pln|ZŁ).*?)\)/i,
        ) ||
        vehicle.exterior_color.match(/-\s*([\d\s,.]+\s*(?:PLN|zł|pln|ZŁ).*?)/i) ||
        vehicle.exterior_color.match(/(\d[\d\s]*\s*(?:PLN|zł|pln|ZŁ))/i);

      if (match) {
        price = match[1] || match[0];
        name = `Lakier: ${vehicle.exterior_color
          .replace(match[0], "")
          .replace(/\(\s*\)/, "")
          .trim()}`;
      }
      factoryOptions.unshift({ name, price, category: "Fabryczna" });
    }
  }

  const hasPaidOptions = factoryOptions.length > 0 || serviceOptions.length > 0;

  if (vehicle.verification_status === "processing") {
    return (
      <div className="bg-white rounded-xl border border-blue-200 shadow-sm p-4 sm:p-5 flex items-center justify-between opacity-80 animate-pulse">
        <div className="flex items-center gap-4">
          <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
          <div className="flex flex-col">
            <h3 className="text-sm font-semibold text-slate-800">
              Przetwarzanie dokumentu...
            </h3>
            <span className="text-xs text-slate-500 max-w-sm">
              Trwa analiza wgrywanego pliku przez Google Gemini. Nie zamykaj strony jeśli chcesz obserwować postęp, 
              ale możesz to zrobić - plik i tak zostanie przetworzony przez serwer.
            </span>
          </div>
        </div>
        <div className="text-right flex flex-col items-end">
            <span className="text-xs font-medium bg-blue-50 text-blue-700 px-3 py-1 rounded-full border border-blue-100 uppercase tracking-widest hidden sm:block">
              W toku
            </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group bg-white rounded-xl border transition-all duration-200 overflow-hidden",
        isExpanded ? "border-blue-200 shadow-md ring-1 ring-blue-50" : "border-slate-200 shadow-sm hover:border-slate-300 hover:shadow-md",
      )}
    >
      {/* --- COLLAPSED STATE (HEADER ROW) --- */}
      <div
        className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
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
          {vehicle.emissions && vehicle.emissions !== "Brak" && vehicle.emissions !== "-" && (
            <div className="flex gap-2 mt-1.5">
              <span className="inline-flex items-center rounded-full bg-slate-50 border border-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
                WLTP: {vehicle.emissions}
              </span>
              {vehicle.wheels && vehicle.wheels !== "Brak" && (
                <span className="inline-flex items-center rounded-full bg-slate-50 border border-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
                  Koła: {vehicle.wheels}
                </span>
              )}
            </div>
          )}
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

      {/* --- EXPANDED STATE (ACCORDION BODY) --- */}
      {isExpanded && (
        <div className="border-t border-slate-100 bg-slate-50/50 p-4 sm:p-6 animate-in fade-in slide-in-from-top-2 duration-300 ease-out">
          
          {mappedData && (
            <div className="mb-6 flex flex-col gap-1.5 text-sm text-slate-700">
               <div className="flex items-start"><span className="text-slate-400 w-32 shrink-0">Marka:</span> <span className="font-semibold">{mappedData.brand || "Brak"}</span></div>
               <div className="flex items-start"><span className="text-slate-400 w-32 shrink-0">Model:</span> <span className="font-semibold">{mappedData.model || "Brak"}</span></div>
               <div className="flex items-start"><span className="text-slate-400 w-32 shrink-0">Wersja wyposażenia:</span> <span className="font-semibold">{mappedData.trim_level || "Brak"}</span></div>
               <div className="flex items-start"><span className="text-slate-400 w-32 shrink-0">Skrzynia / Napęd:</span> <span className="font-semibold">{mappedData.transmission || "Brak"}</span></div>
               <div className="flex items-start"><span className="text-slate-400 w-32 shrink-0">Paliwo:</span> <span className="font-semibold">{mappedData.fuel || "Brak"}</span></div>
               <div className="flex items-start"><span className="text-slate-400 w-32 shrink-0">Typ:</span> <span className="font-semibold">{mappedData.vehicle_type || "Brak"}</span></div>
            </div>
          )}

          {/* Top Section: Price Summary Visual */}
          <div className="mb-8">
            <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              <Banknote className="w-4 h-4 mr-2 text-slate-400" />
              Podsumowanie Finansowe
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Base Price */}
              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col items-center text-center">
                <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 mb-1">Cena Bazowa</div>
                <div className="text-sm font-semibold text-slate-800"><PriceDualFormat priceStr={vehicle.base_price} align="center" /></div>
              </div>
              
              {/* Options Price */}
              <div className="relative bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col items-center text-center">
                <div className="hidden md:flex absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-100 border border-slate-200 items-center justify-center text-slate-400 text-xs font-bold z-10">
                  +
                </div>
                <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 mb-1">Opcje Dodatkowe</div>
                <div className="text-sm font-semibold text-slate-800"><PriceDualFormat priceStr={vehicle.options_price} align="center" /></div>
              </div>

              {/* Discount Selector */}
              <div className="relative bg-blue-50/50 pt-5 pb-3 px-4 rounded-lg border border-blue-200 shadow-sm flex flex-col items-center text-center">
                <div className="hidden md:flex absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-100 border border-slate-200 items-center justify-center text-slate-400 text-xs font-bold z-10">
                  -
                </div>
                
                {/* Absolute positioned custom input always visible */}
                <div className="absolute top-1.5 right-1.5 flex items-center bg-white rounded shadow-sm border border-blue-200 overflow-hidden z-10 transition-all">
                   <input 
                     type="text"
                     className={cn(
                       "w-10 text-right text-xs px-1.5 py-1 focus:outline-none font-bold transition-colors",
                       discountMode === "custom" ? "text-blue-700 bg-white" : "text-slate-400 bg-slate-50"
                     )}
                     value={customDiscountPctRaw}
                     onFocus={() => setDiscountMode("custom")}
                     onChange={(e) => {
                       const raw = e.target.value.replace(/[^0-9]/g, '');
                       const num = parseInt(raw, 10);
                       if (!raw) {
                         setCustomDiscountPctRaw("");
                       } else if (!isNaN(num) && num >= 0 && num <= 100) {
                         setCustomDiscountPctRaw(raw);
                       }
                       setDiscountMode("custom");
                     }}
                     placeholder="0"
                     title="Wpisz własny rabat"
                   />
                   <span className={cn(
                     "text-xs font-bold pr-1.5 py-1 border-l transition-colors",
                     discountMode === "custom" ? "text-slate-400 bg-slate-50 border-blue-100" : "text-slate-400 bg-slate-100 border-slate-200"
                   )}>%</span>
                </div>


                <div className="text-[10px] uppercase font-semibold tracking-wider text-blue-600 mb-1.5 w-full text-left">Wybór Rabatu</div>
                <select 
                  className="w-full bg-white border border-blue-200 text-slate-700 font-medium text-xs rounded px-2 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none cursor-pointer"
                  value={discountMode}
                  onChange={(e) => setDiscountMode(e.target.value as "offer" | "suggested" | "custom")}
                >
                  <option value="offer">Rabat z oferty ({isDealerOffer ? offerDiscountPercentage : 0}%)</option>
                  <option value="suggested" disabled={suggestedDiscountPct === 0}>
                    Sugerowany z BD ({suggestedDiscountPct}%)
                  </option>
                  <option value="custom">Własny rabat</option>
                </select>

              </div>

              {/* Final / Discounted Price */}
              <div className={cn(
                "relative p-4 rounded-lg shadow-sm flex flex-col items-center justify-center text-center border",
                activeDiscountPct > 0 ? "bg-emerald-50/50 border-emerald-200" : "bg-white border-slate-200"
              )}>
                 <div className="hidden md:flex absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-100 border border-slate-200 items-center justify-center text-slate-400 text-xs font-bold z-10">
                  =
                </div>
                <div className="flex items-center text-[10px] uppercase font-semibold tracking-wider mb-1">
                  <span className={activeDiscountPct > 0 ? "text-emerald-700" : "text-slate-400"}>Suma po rabacie</span>
                </div>
                <div className={cn("text-base font-bold flex justify-center w-full", activeDiscountPct > 0 ? "text-emerald-700" : "text-slate-800")}>
                  <PriceDualFormat 
                    priceStr={totalCatalogPrice > 0 ? formatCalculatedPrice(activeFinalPrice) : "Brak"} 
                    align="center" 
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Left Col: Standard Equipment */}
            {vehicle.standard_equipment && vehicle.standard_equipment.length > 0 && (
              <div>
                <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Wyposażenie Standardowe
                </h4>
                <div className="bg-white rounded border border-slate-200 overflow-hidden shadow-sm h-64 overflow-y-auto custom-scrollbar">
                  <ul className="divide-y divide-slate-100">
                    {vehicle.standard_equipment.map((item, idx) => (
                      <li key={idx} className="px-4 py-2 text-[11px] text-slate-600 hover:bg-slate-50 transition-colors flex items-start gap-2">
                         <div className="w-1.5 h-1.5 rounded-full bg-slate-300 mt-1.5 flex-shrink-0" />
                         <span>{renderOptionName(item)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Right Col: Paid Options */}
            {hasPaidOptions && (
              <div>
                <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                  <Sparkles className="w-4 h-4 mr-2" />
                  Płatne Opcje & Usługi
                </h4>
                <div className="bg-white rounded border border-slate-200 p-4 shadow-sm h-64 overflow-y-auto custom-scrollbar space-y-5">
                  
                  {factoryOptions.length > 0 && (
                    <div>
                      <h5 className="text-[11px] font-bold text-slate-800 mb-2 font-mono uppercase">Opcje Fabryczne</h5>
                      <ul className="space-y-2">
                        {factoryOptions.map((opt, idx) => (
                          <li key={idx} className="flex flex-col xl:flex-row xl:items-start justify-between gap-1 text-[11px] pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                            <span className="text-slate-600 font-medium pt-1">{renderOptionName(opt.name)}</span>
                            <span className="text-right text-slate-800 font-semibold bg-slate-50 px-2.5 py-1 rounded xl:ml-4 flex-shrink-0">
                               <PriceDualFormat priceStr={opt.price} align="right" inline={true} />
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {serviceOptions.length > 0 && (
                    <div>
                      <h5 className="text-[11px] font-bold text-slate-800 mb-2 font-mono uppercase">Dodatki Serwisowe / Akcesoria</h5>
                      <ul className="space-y-3">
                        {serviceOptions.map((opt, idx) => (
                          <li key={idx} className="flex flex-col xl:flex-row xl:items-start justify-between gap-1 text-[11px] pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                            <span className="text-slate-600 font-medium pt-1">{renderOptionName(opt.name)}</span>
                            <span className="text-right text-slate-800 font-semibold bg-slate-50 px-2.5 py-1 rounded xl:ml-4 flex-shrink-0">
                               <PriceDualFormat priceStr={opt.price} align="right" inline={true} />
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                </div>
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-col items-end gap-3 pt-4 border-t border-slate-200">
             <div className="flex justify-end items-center gap-3">
               <button
                 onClick={(e) => {
                   e.stopPropagation();
                   // Mock logic for creating a new calculation
                   const mockDate = new Date();
                   const year = mockDate.getFullYear();
                   const month = String(mockDate.getMonth() + 1).padStart(2, '0');
                   const randomId = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
                   const numerKalkulacji = `K/${year}/${month}/${randomId}`;
                   
                   console.log(`[MOCK] Utworzono nową kalkulację: ${numerKalkulacji} na bazie pojazdu: ${vehicle.id}`);
                   
                   const params = new URLSearchParams();
                   params.set('id', vehicle.id); // for now pass vehicle id as the context, or we could pass new calculation id
                   params.set('kalkulacja', numerKalkulacji); // Mock info
                   params.set('aktywnyRabatProcent', activeDiscountPct.toString());
                   params.set('aktywnaCenaKoncowa', activeFinalPrice.toString());
                   // In real app, we would await API call to create Calculation here
                   
                   window.dispatchEvent(
                     new CustomEvent('switchTab', {
                       detail: { tabIndex: 2, urlParams: params },
                     })
                   );
                 }}
                 className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md transition-all shadow-sm"
               >
                 <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                 Zrób kalkulację
               </button>

               <button
                 onClick={(e) => {
                   e.stopPropagation();
                   setIsOverrideModalOpen(!isOverrideModalOpen);
                 }}
                 className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-emerald-50 border border-emerald-100 text-emerald-700 hover:bg-emerald-100 hover:border-emerald-200 hover:shadow-sm transition-all shadow-sm"
               >
                 <Wand2 className="w-3.5 h-3.5 mr-2" />
                 Modyfikacja manualna
               </button>

               <button
                 onClick={(e) => {
                   e.stopPropagation();
                   handleOpenSavedJson(vehicle.id, `${vehicle.brand} ${vehicle.model}`);
                 }}
                 className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 hover:shadow-sm transition-all shadow-sm"
               >
                 <Database className="w-3.5 h-3.5 mr-2" />
                 Dane JSON
               </button>
               {vehicle.raw_pdf_url && (
                 <button
                   onClick={(e) => {
                     e.stopPropagation();
                     if (vehicle.raw_pdf_url) setIsViewerOpen(true);
                   }}
                   className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-blue-50 border border-blue-100 text-blue-700 hover:bg-blue-100 hover:border-blue-200 hover:shadow-sm transition-all shadow-sm"
                 >
                   <ExternalLink className="w-3.5 h-3.5 mr-2" />
                   Otwórz dokument
                 </button>
               )}
               <button
                 onClick={(e) => {
                   e.stopPropagation();
                   if (window.confirm("Czy na pewno chcesz usunąć tę plakietkę? Istniejące kalkulacje na jej bazie nie zostaną usunięte.")) {
                       // We trigger a custom event that will be caught by the parent component,
                       // or we can pass a handleDelete prop. Let's trigger a custom event for looser coupling or use a prop if available.
                       // For now, let's use a custom event since VehicleRowCard doesn't seem to have a handleDelete prop.
                       const event = new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } });
                       window.dispatchEvent(event);
                   }
                 }}
                 className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-red-50 border border-red-100 text-red-600 hover:bg-red-100 hover:border-red-200 hover:shadow-sm transition-all shadow-sm"
               >
                 <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" className="mr-2"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                 Usuń
               </button>
             </div>

              {isOverrideModalOpen && (
               <div className="w-full mt-2 p-4 bg-slate-50 border border-slate-200 rounded-lg animate-in fade-in slide-in-from-top-2">
                 <h5 className="text-[11px] font-bold text-slate-700 mb-2 flex items-center uppercase tracking-wider">
                   <Wand2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" /> Nadpisywanie Danych z użyciem AI (Flash)
                 </h5>
                 <div className="flex gap-2">
                   <input
                     type="text"
                     placeholder="np. Dodaj hak holowniczy, moc silnika to 300KM, ma napęd AWD..."
                     value={overridePrompt}
                     onChange={(e) => setOverridePrompt(e.target.value)}
                     className="flex-1 px-3 py-2 text-sm rounded-md border border-slate-300 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 shadow-sm"
                     onKeyDown={(e) => {
                       if (e.key === "Enter") handleManualOverride();
                     }}
                   />
                   <button
                     onClick={handleManualOverride}
                     disabled={isOverriding || !overridePrompt.trim()}
                     className="px-4 py-2 bg-emerald-600 text-white rounded-md font-medium text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center shadow-sm transition-colors"
                   >
                     {isOverriding ? <Loader2 className="w-4 h-4 animate-spin mr-1.5" /> : null}
                     {isOverriding ? "Korygowanie..." : "Zastosuj"}
                   </button>
                 </div>
                 <p className="text-[10px] text-slate-500 mt-2">
                   Algorytm chirurgicznie zedytuje wyłącznie zlecane parametry w obrębie Cyfrowego Bliźniaka, zachowując 100% spójności reszty dokumentu. Zmiana widoczna będzie po odświeżeniu.
                 </p>
               </div>
             )}


          </div>
        </div>
      )}

      <DocumentViewerModal
        isOpen={isViewerOpen}
        onClose={() => setIsViewerOpen(false)}
        pdfUrl={vehicle.raw_pdf_url}
        documentName={`${vehicle.brand} ${vehicle.model} - Dokument`}
      />
    </div>
  );
}


// --- MAIN TABLE CONTAINER ---
interface VehicleTableProps {
  savedVehicles: FleetVehicleView[];
  isLoadingSaved: boolean;
  globalSearchQuery: string;
  isSearching: boolean;
  setGlobalSearchQuery: (query: string) => void;
  handleGlobalSearch: (e: React.FormEvent) => void;
  fetchSavedVehicles: () => void;
  handleOpenSavedJson: (vehicleId: string, titleName: string) => void;
  handleDeleteVehicle?: (vehicleId: string) => void;
}

export function VehicleTable({
  savedVehicles,
  isLoadingSaved,
  globalSearchQuery,
  isSearching,
  setGlobalSearchQuery,
  handleGlobalSearch,
  fetchSavedVehicles,
  handleOpenSavedJson,
  handleDeleteVehicle,
}: VehicleTableProps) {
  // Listen for the custom event from the nested card
  useEffect(() => {
    const handleCustomDelete = (e: Event) => {
        const customEvent = e as CustomEvent;
        if (customEvent.detail && customEvent.detail.vehicleId && handleDeleteVehicle) {
            handleDeleteVehicle(customEvent.detail.vehicleId);
        }
    };
    window.addEventListener('deleteVehicle', handleCustomDelete);
    return () => {
        window.removeEventListener('deleteVehicle', handleCustomDelete);
    };
  }, [handleDeleteVehicle]);

  return (
    <div className="w-full">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
        <div>
          <h2 className="text-lg font-medium text-slate-900 tracking-tight">
            Przetworzone pojazdy
          </h2>
          <p className="text-xs text-slate-500 mt-1 flex items-center">
            <Info className="w-3 h-3 mr-1" />
            Baza zsynchronizowana z modelem
            <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded ml-1 font-mono text-[10px] font-semibold border border-blue-100">
              v2.0_digital_twin
            </span>
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <form
            onSubmit={handleGlobalSearch}
            className="relative flex-1 min-w-[280px]"
          >
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <input
              type="text"
              value={globalSearchQuery}
              onChange={(e) => setGlobalSearchQuery(e.target.value)}
              placeholder="Wyszukaj z użyciem AI (Gemini)..."
              className="w-full pl-9 pr-20 py-2.5 border border-slate-200 bg-white rounded-lg text-sm outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all shadow-sm"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[10px] uppercase font-bold text-slate-600 hover:text-blue-600 px-3 py-1.5 rounded-md bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 transition-colors disabled:opacity-50"
            >
              {isSearching ? (
                <Loader2 className="w-3 h-3 animate-spin mx-auto" />
              ) : (
                "Szukaj"
              )}
            </button>
          </form>

          <button
            onClick={fetchSavedVehicles}
            className="p-2.5 text-slate-400 hover:text-blue-600 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-100 shadow-sm rounded-lg transition-all"
            title="Odśwież listę"
          >
            <RefreshCw
              className={cn(
                "w-4 h-4",
                isLoadingSaved && "animate-spin text-blue-500",
              )}
            />
          </button>
        </div>
      </div>

      {isLoadingSaved && savedVehicles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-white rounded-2xl border border-dashed border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
          <p className="text-sm font-medium text-slate-600">Wczytywanie floty...</p>
        </div>
      ) : savedVehicles.length === 0 ? (
        <div className="border border-dashed border-slate-300 bg-slate-50 rounded-2xl p-16 text-center flex flex-col items-center justify-center shadow-inner">
          <Database className="w-10 h-10 text-slate-300 mb-4" />
          <p className="text-slate-700 text-base font-semibold">Brak wyekstrahowanych dokumentów.</p>
          <p className="text-sm text-slate-500 mt-2 max-w-sm">
            Prześlij nowe oferty i cenniki powyżej, aby automatycznie utworzyć z nich ustrukturyzowane wpisy.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <style dangerouslySetInnerHTML={{__html: `
            .custom-scrollbar::-webkit-scrollbar { width: 6px; }
            .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
            .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 10px; }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #94a3b8; }
          `}} />
          {savedVehicles.map((vehicle) => (
            <VehicleRowCard
              key={vehicle.id}
              vehicle={vehicle}
              handleOpenSavedJson={handleOpenSavedJson}
              onRefresh={fetchSavedVehicles}
            />
          ))}
        </div>
      )}
    </div>
  );
}

