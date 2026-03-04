import { Banknote, CheckCircle2, Database, Loader2, Sparkles, Wrench, ChevronDown, ChevronUp, CircleDot, AlertTriangle } from "lucide-react";
import type { JSX } from "react";
import { cn } from "../ui/DocumentCard";
import type { FleetVehicleView } from "../../types";
import { ServiceOptionsManager } from "../../../components/Calculator/ServiceOptionsManager";
import type { ExtractedServiceOption } from "../../../components/Calculator/ServiceOptionsManager";
import { PriceDualFormat } from "./PriceDualFormat";
import { NetGrossInput } from "./NetGrossInput";
import { LinkedIndicator } from "./LinkedIndicator";
import { useState, useMemo } from "react";

interface VehicleFinancialOptionsProps {
  vehicle: FleetVehicleView;
  // Prices
  totalCatalogPrice: number;
  activeFinalPrice: number;
  dynamicTotalOptionsPrice: number;
  // Discount state
  discountMode: "offer" | "suggested" | "custom";
  setDiscountMode: (mode: "offer" | "suggested" | "custom") => void;
  customDiscountPctRaw: string | number;
  setCustomDiscountPctRaw: (val: string) => void;
  // Other derived
  isDealerOffer: boolean;
  offerDiscountPercentage: number;
  suggestedDiscountPct: number;
  activeDiscountPct: number;
  formatCalculatedPrice: (val: number) => string;
  // Factory Options CRUD
  customFactoryOptions: { id: string; name: string; price_net: number; category: string }[];
  handleUpdateFactoryOptionName: (id: string, newName: string) => void;
  handleUpdateFactoryOptionPrice: (id: string, newPrice: number) => void;
  handleRemoveFactoryOption: (id: string) => void;
  handleAddManualFactoryOption: () => void;
  hasFactoryOptions: boolean;
  renderOptionName: (name: string) => JSX.Element;
  // Service Options CRUD
  customServiceOptions: { id: string; name: string; price_net: number; category: string; include_in_wr?: boolean }[];
  handleUpdateServiceOptionName: (id: string, newName: string) => void;
  handleUpdateServiceOptionPrice: (id: string, newPrice: number) => void;
  handleUpdateServiceOptionIncludeInWr: (id: string, include: boolean) => void;
  handleRemoveServiceOption: (id: string) => void;
  handleAddManualServiceOption: () => void;
  handleRestoreAllOptions: () => void;
  handleSaveAllOptions: () => Promise<void>;
  isSavingServices: boolean;
  handleServiceOptionExtracted: (option: ExtractedServiceOption) => void;
  // Financial parameters
  wiborPct: number;
  setWiborPct: (val: number) => void;
  marginPct: number;
  setMarginPct: (val: number) => void;
  pricingMarginPct: number;
  setPricingMarginPct: (val: number) => void;
  depreciationPct: number;
  initialDepositPct: number;
  setInitialDepositPct: (val: number) => void;
  otherServiceCosts: number;
  setOtherServiceCosts: (val: number) => void;
  // Toggles
  expressPaysInsurance: boolean;
  setExpressPaysInsurance: (val: boolean) => void;
  replacementCar: boolean;
  setReplacementCar: (val: boolean) => void;
  gpsRequired: boolean;
  setGpsRequired: (val: boolean) => void;
  includeServicing: boolean;
  setIncludeServicing: (val: boolean) => void;
  hookInstallation: boolean;
  setHookInstallation: (val: boolean) => void;
  // Tire parameters
  tireClass: string;
  setTireClass: (val: string) => void;
  tireCountMode: string;
  setTireCountMode: (val: string) => void;
  tireCostCorrectionEnabled: boolean;
  setTireCostCorrectionEnabled: (val: boolean) => void;
  tireCostCorrection: number;
  setTireCostCorrection: (val: number) => void;
  // Service cost type
  serviceCostType: "ASO" | "nonASO";
  setServiceCostType: (val: "ASO" | "nonASO") => void;
  // Vehicle vintage & metalic
  vehicleVintage: "current" | "previous";
  setVehicleVintage: (val: "current" | "previous") => void;
  isMetalic: boolean;
  setIsMetalic: (val: boolean) => void;
  isMetalicAutoDetected: boolean;
  // Czynsz inicjalny netto/brutto
  activeFinalPriceForDeposit: number;
}

const TIRE_CLASS_OPTIONS = [
  { value: "Budget", label: "Budget" },
  { value: "Medium", label: "Medium" },
  { value: "Premium", label: "Premium" },
  { value: "Wzmocnione Budget", label: "Wzmocnione Budget" },
  { value: "Wzmocnione Medium", label: "Wzmocnione Medium" },
  { value: "Wzmocnione Premium", label: "Wzmocnione Premium" },
  { value: "Wielosezon Budget", label: "Wielosezon Budget" },
  { value: "Wielosezon Medium", label: "Wielosezon Medium" },
  { value: "Wielosezon Premium", label: "Wielosezon Premium" },
  { value: "Wielosezon Wzmocnione Budget", label: "Wielosez.+Wzm. Budget" },
  { value: "Wielosezon Wzmocnione Medium", label: "Wielosez.+Wzm. Medium" },
  { value: "Wielosezon Wzmocnione Premium", label: "Wielosez.+Wzm. Premium" },
];

const TIRE_COUNT_OPTIONS = [
  { value: "auto", label: "Auto (z przebiegu)" },
  { value: "1", label: "1 komplet" },
  { value: "1.5", label: "1,5 kompletu" },
  { value: "2", label: "2 komplety" },
  { value: "2.5", label: "2,5 kompletu" },
];

export function VehicleFinancialOptions(props: VehicleFinancialOptionsProps) {
  const {
    vehicle, totalCatalogPrice, activeFinalPrice, dynamicTotalOptionsPrice,
    discountMode, setDiscountMode, customDiscountPctRaw, setCustomDiscountPctRaw,
    isDealerOffer, offerDiscountPercentage, suggestedDiscountPct, activeDiscountPct,
    formatCalculatedPrice, customFactoryOptions, handleUpdateFactoryOptionName,
    handleUpdateFactoryOptionPrice, handleRemoveFactoryOption, handleAddManualFactoryOption,
    hasFactoryOptions, renderOptionName, customServiceOptions, handleUpdateServiceOptionName,
    handleUpdateServiceOptionPrice, handleUpdateServiceOptionIncludeInWr,
    handleRemoveServiceOption, handleAddManualServiceOption, handleRestoreAllOptions,
    handleSaveAllOptions, isSavingServices, handleServiceOptionExtracted,
    wiborPct, setWiborPct, marginPct, setMarginPct, pricingMarginPct, setPricingMarginPct, depreciationPct,
    initialDepositPct, setInitialDepositPct, otherServiceCosts, setOtherServiceCosts,
    expressPaysInsurance, setExpressPaysInsurance, replacementCar, setReplacementCar,
    gpsRequired, setGpsRequired, includeServicing, setIncludeServicing,
    hookInstallation, setHookInstallation,
    tireClass, setTireClass, tireCountMode, setTireCountMode,
    tireCostCorrectionEnabled, setTireCostCorrectionEnabled,
    tireCostCorrection, setTireCostCorrection,
    serviceCostType, setServiceCostType,
    vehicleVintage, setVehicleVintage,
    isMetalic, setIsMetalic, isMetalicAutoDetected,
    activeFinalPriceForDeposit,
  } = props;

  const [isStandardEquipmentOpen, setIsStandardEquipmentOpen] = useState(false);

  // Extracted wheel size from AI
  const extractedWheelSize = useMemo(() => {
    const wheels = vehicle.wheels || "";
    const match = wheels.match(/(\d{2})/);
    return match ? parseInt(match[1], 10) : null;
  }, [vehicle.wheels]);

  // Czynsz inicjalny calculated amounts
  const depositAmountNet = activeFinalPriceForDeposit * (initialDepositPct / 100);
  const depositAmountGross = depositAmountNet * 1.23;


  return (
    <>
      {/* Top Section: Price Summary Visual */}
      <div className="mb-8 mt-6">
        <div className="flex justify-between items-center mb-3">
          <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400">
            <Banknote className="w-4 h-4 mr-2 text-slate-400" />
            Podsumowanie Finansowe
          </h4>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Base Price */}
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col items-center text-center">
            <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 mb-1">Cena Bazowa</div>
            <div className="text-sm font-semibold text-slate-800"><PriceDualFormat priceStr={vehicle.base_price} align="center" /></div>
          </div>
          
          {/* Options Price */}
          <div className="relative bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col items-center text-center">
            <div className="hidden md:flex absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-100 border border-slate-200 items-center justify-center text-slate-400 text-xs font-bold z-10">+</div>
            <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 mb-1">Opcje Dodatkowe</div>
            <div className="text-sm font-semibold text-slate-800"><PriceDualFormat priceStr={formatCalculatedPrice(dynamicTotalOptionsPrice)} align="center" /></div>
          </div>

          {/* Discount Selector */}
          <div className="relative bg-blue-50/50 pt-5 pb-3 px-4 rounded-lg border border-blue-200 shadow-sm flex flex-col items-center text-center">
            <div className="hidden md:flex absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-100 border border-slate-200 items-center justify-center text-slate-400 text-xs font-bold z-10">-</div>
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

            {/* Alert: offer discount beats DB discount */}
            {isDealerOffer && suggestedDiscountPct > 0 && offerDiscountPercentage > suggestedDiscountPct && (
              <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2 text-[11px] text-amber-800 text-left animate-in fade-in duration-300 w-full">
                <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-bold">Dealer daje lepszy rabat!</span>
                  <br />
                  Oferta: {offerDiscountPercentage}% vs BD: {suggestedDiscountPct}%{" "}
                  <span className="font-semibold">(+{(offerDiscountPercentage - suggestedDiscountPct).toFixed(1)} pp.)</span>
                  <br />
                  <span className="text-amber-600 font-medium">→ Sugestia: renegocjuj warunki flotowe</span>
                </div>
              </div>
            )}
          </div>

          {/* Final / Discounted Price */}
          <div className={cn(
            "relative p-4 rounded-lg shadow-sm flex flex-col items-center justify-center text-center border",
            activeDiscountPct > 0 ? "bg-emerald-50/50 border-emerald-200" : "bg-white border-slate-200"
          )}>
             <div className="hidden md:flex absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-100 border border-slate-200 items-center justify-center text-slate-400 text-xs font-bold z-10">=</div>
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

      <div className="grid grid-cols-1 gap-8">
        {/* Standard Equipment */}
        {vehicle.standard_equipment && vehicle.standard_equipment.length > 0 && (
          <div>
            <button
              onClick={() => setIsStandardEquipmentOpen(!isStandardEquipmentOpen)}
              className="flex items-center justify-between w-full hover:bg-slate-50 p-2 -ml-2 rounded transition-colors group cursor-pointer"
            >
              <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 group-hover:text-slate-600 transition-colors">
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Wyposażenie Standardowe
              </h4>
              <div className="text-slate-400 group-hover:text-slate-600">
                {isStandardEquipmentOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </button>
            
            {isStandardEquipmentOpen && (
              <div className="bg-white rounded border border-slate-200 overflow-hidden shadow-sm h-64 overflow-y-auto custom-scrollbar mt-2 animate-in slide-in-from-top-2 fade-in duration-200">
                <ul className="divide-y divide-slate-100">
                  {vehicle.standard_equipment.map((item, idx) => (
                    <li key={idx} className="px-4 py-2 text-[11px] text-slate-600 hover:bg-slate-50 transition-colors flex items-start gap-2">
                       <div className="w-1.5 h-1.5 rounded-full bg-slate-300 mt-1.5 flex-shrink-0" />
                       <span>{renderOptionName(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Factory Paid Options */}
        {hasFactoryOptions && (
          <div>
            <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              <Sparkles className="w-4 h-4 mr-2" />
              Płatne Opcje & Usługi
            </h4>
            <div className="bg-white rounded border border-slate-200 p-4 shadow-sm h-64 overflow-y-auto custom-scrollbar space-y-5">
              {customFactoryOptions.length > 0 ? (
                <div>
                  <h5 className="text-[11px] font-bold text-slate-800 mb-2 font-mono uppercase">Opcje Fabryczne</h5>
                  <ul className="space-y-3">
                    {customFactoryOptions.map((opt) => (
                      <li key={opt.id} className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 text-[11px] pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                        <input 
                          type="text" 
                          className="flex-1 px-3 py-1.5 border border-slate-200 rounded text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                          value={opt.name}
                          onChange={(e) => handleUpdateFactoryOptionName(opt.id, e.target.value)}
                          placeholder="Nazwa Opcji Fabrycznej"
                        />
                        <div className="flex items-center gap-2 mt-2 xl:mt-0 xl:w-auto w-full justify-between xl:justify-end">
                           <NetGrossInput netValue={opt.price_net} onChangeNet={(newVal) => handleUpdateFactoryOptionPrice(opt.id, newVal)} />
                           <button onClick={() => handleRemoveFactoryOption(opt.id)} className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors" title="Usuń pozycję">
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                           </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="py-6 text-center text-slate-400 text-sm">
                    Brak zdefiniowanych opcji fabrycznych dla tego pojazdu.
                </div>
              )}
              <div className="flex flex-col gap-4 pt-2 border-t border-slate-100 mt-2">
                 <div className="flex flex-wrap items-center justify-between gap-4">
                     <button onClick={handleAddManualFactoryOption} className="flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-all shadow-sm">
                       <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                       Dodaj ręcznie
                     </button>
                 </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Service Options CRUD */}
      <div className="mt-8">
          <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            <Wrench className="w-4 h-4 mr-2" />
            Usługi Serwisowe / Dodatkowe (Digital Twin)
          </h4>
           <div className="bg-white rounded border border-slate-200 p-4 shadow-sm space-y-4">
              {customServiceOptions.length > 0 ? (
                  <ul className="space-y-3">
                    {customServiceOptions.map((opt) => (
                      <li key={opt.id} className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 text-[11px] pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                        <input type="text" className="flex-1 px-3 py-1.5 border border-slate-200 rounded text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500" value={opt.name} onChange={(e) => handleUpdateServiceOptionName(opt.id, e.target.value)} placeholder="Nazwa Usługi" />
                        <div className="flex items-center gap-2 mt-2 xl:mt-0 xl:w-auto w-full justify-between xl:justify-end">
                           <label className="flex items-center gap-1.5 cursor-pointer text-[10px] text-slate-500 hover:text-slate-700 mr-2 border border-slate-100 px-2 py-1 rounded bg-slate-50/50">
                             <input type="checkbox" checked={opt.include_in_wr || false} onChange={(e) => handleUpdateServiceOptionIncludeInWr(opt.id, e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3 w-3" />
                             Dolicz do WR
                           </label>
                           <NetGrossInput netValue={opt.price_net} onChangeNet={(newVal) => handleUpdateServiceOptionPrice(opt.id, newVal)} />
                           <button onClick={() => handleRemoveServiceOption(opt.id)} className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors" title="Usuń pozycję">
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                           </button>
                        </div>
                      </li>
                    ))}
                  </ul>
              ) : (
                <div className="py-6 text-center text-slate-400 text-sm">
                    Brak zdefiniowanych operacji serwisowych dla tego pojazdu.
                </div>
              )}
              <div className="flex flex-col gap-4 pt-2 border-t border-slate-100">
                 <div className="flex flex-wrap items-center justify-between gap-4">
                     <button onClick={handleAddManualServiceOption} className="flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-all shadow-sm">
                       <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                       Dodaj ręcznie
                     </button>
                     <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto mt-2 sm:mt-0">
                        <button onClick={handleRestoreAllOptions} className="w-full sm:w-auto flex items-center justify-center text-[11px] font-semibold px-4 py-2 rounded text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors" title="Odrzuć zmiany i przywróć opcje wyekstrahowane z bazy">
                           <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                           Przywróć JSON
                        </button>
                        <button onClick={handleSaveAllOptions} disabled={isSavingServices} className="w-full sm:w-auto flex items-center justify-center text-xs font-semibold px-6 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-all shadow-sm">
                           {isSavingServices ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Database className="w-4 h-4 mr-2" />}
                           {isSavingServices ? "Zapisywanie..." : "Zapisz Opcje i Usługi"}
                        </button>
                     </div>
                 </div>
                 <div className="w-full pt-2 mt-2 border-t border-slate-50">
                     <ServiceOptionsManager onOptionExtracted={handleServiceOptionExtracted} />
                 </div>
              </div>
           </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* OPONY (Tires) Section - NEW */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="mt-8">
        <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
          <CircleDot className="w-4 h-4 mr-2" />
          Opony
        </h4>
        <div className="bg-white rounded border border-slate-200 p-4 shadow-sm">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            {/* Wheel size from AI */}
            <div>
              <label className="flex items-center text-[10px] font-bold uppercase text-slate-500 mb-1">
                Średnica felgi (AI)
                <LinkedIndicator tableName="koszty_opon" isLinked={extractedWheelSize !== null} />
              </label>
              <div className="w-full text-xs p-1.5 border border-slate-200 rounded bg-slate-50 text-slate-600 font-semibold">
                {extractedWheelSize ? `${extractedWheelSize}"` : "Brak danych"}
                {vehicle.wheels && <span className="text-[10px] text-slate-400 ml-1">({vehicle.wheels})</span>}
              </div>
            </div>

            {/* Tire class dropdown */}
            <div>
              <label className="flex items-center text-[10px] font-bold uppercase text-slate-500 mb-1">
                Klasa opon
                <LinkedIndicator tableName="koszty_opon" isLinked={true} />
              </label>
              <select
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer font-medium text-slate-700"
                value={tireClass}
                onChange={(e) => setTireClass(e.target.value)}
              >
                {TIRE_CLASS_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Tire count */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">Liczba kompletów</label>
              <select
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer font-medium text-slate-700"
                value={tireCountMode}
                onChange={(e) => setTireCountMode(e.target.value)}
              >
                {TIRE_COUNT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Tire cost correction */}
            <div>
              <label className="flex items-center gap-2 text-[10px] font-bold uppercase text-slate-500 mb-1">
                <input
                  type="checkbox"
                  checked={tireCostCorrectionEnabled}
                  onChange={(e) => setTireCostCorrectionEnabled(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3 w-3"
                />
                Korekta kosztu opon (brutto)
              </label>
              <input
                type="number"
                step="1"
                className={cn(
                  "w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500",
                  !tireCostCorrectionEnabled && "bg-slate-50 text-slate-400 cursor-not-allowed"
                )}
                value={tireCostCorrection}
                onChange={(e) => setTireCostCorrection(parseFloat(e.target.value) || 0)}
                disabled={!tireCostCorrectionEnabled}
                placeholder="0"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* Calculator Parameters Section */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="mt-8">
        <h4 className="flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          Parametry Kalkulacji
        </h4>
        <div className="bg-white rounded border border-slate-200 p-4 shadow-sm">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">WIBOR (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={wiborPct} onChange={e => setWiborPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">Marża bankowa (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={marginPct} onChange={e => setMarginPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">Wskaźnik amortyzacji (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none bg-slate-50 text-slate-500 cursor-not-allowed" value={depreciationPct} readOnly />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">Marża Sprzedaży LTR (%)</label>
              <input type="number" step="0.1" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={pricingMarginPct} onChange={e => setPricingMarginPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">Czynsz inicjalny (%)</label>
              <div className="flex gap-1.5">
                <input
                  type="number" step="0.1"
                  className="w-16 text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500"
                  value={initialDepositPct}
                  onChange={e => setInitialDepositPct(parseFloat(e.target.value) || 0)}
                />
                <div className="flex-1 text-[9px] text-slate-400 flex flex-col justify-center leading-tight">
                  <span>= {depositAmountNet.toFixed(0)} PLN netto</span>
                  <span>= {depositAmountGross.toFixed(0)} PLN brutto</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 pt-3 border-t border-slate-100">
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">Inne koszty serwisowania (PLN/mc)</label>
              <input type="number" step="1" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={otherServiceCosts} onChange={e => setOtherServiceCosts(parseFloat(e.target.value) || 0)} />
            </div>

            {/* ASO / nonASO Dropdown */}
            <div>
              <label className="flex items-center text-[10px] font-bold uppercase text-slate-500 mb-1">
                Rodzaj kosztów serwisu
                <LinkedIndicator tableName="samar_service_costs" isLinked={true} />
              </label>
              <select
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer font-medium text-slate-700"
                value={serviceCostType}
                onChange={(e) => setServiceCostType(e.target.value as "ASO" | "nonASO")}
              >
                <option value="ASO">ASO (Autoryzowany Serwis)</option>
                <option value="nonASO">Non-ASO (Serwis Niezależny)</option>
              </select>
            </div>

            {/* Rocznik Dropdown */}
            <div>
              <label className="flex items-center text-[10px] font-bold uppercase text-slate-500 mb-1">
                Rocznik pojazdu
                <LinkedIndicator tableName="samar_vintage_depreciation" isLinked={true} />
              </label>
              <select
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer font-medium text-slate-700"
                value={vehicleVintage}
                onChange={(e) => setVehicleVintage(e.target.value as "current" | "previous")}
              >
                <option value="current">Bieżący rocznik</option>
                <option value="previous">Ubiegły rocznik</option>
              </select>
            </div>

            {/* Metalik Toggle */}
            <div>
              <label className="flex items-center text-[10px] font-bold uppercase text-slate-500 mb-1">
                Lakier metalik
                <LinkedIndicator tableName="samar_color_depreciation" isLinked={true} />
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1.5 px-2 border border-slate-200 rounded bg-white">
                <input
                  type="checkbox"
                  checked={isMetalic}
                  onChange={(e) => setIsMetalic(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5"
                />
                <span className="font-medium">{isMetalic ? "Tak (metalik/perłowy)" : "Nie (zwykły lakier)"}</span>
                {isMetalicAutoDetected && (
                  <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 font-semibold ring-1 ring-emerald-200">
                    AI
                  </span>
                )}
              </label>
            </div>
          </div>

          {/* Toggles Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-x-6 gap-y-2 pt-3 border-t border-slate-100">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={expressPaysInsurance} onChange={e => setExpressPaysInsurance(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              Express płaci ubezpieczenie
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={replacementCar} onChange={e => setReplacementCar(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              <span className="flex items-center">Samochód zastępczy <LinkedIndicator tableName="replacement_car_rates" isLinked={true} /></span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={gpsRequired} onChange={e => setGpsRequired(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              <span className="flex items-center">GPS wymagane <LinkedIndicator tableName="control_center" isLinked={true} /></span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={includeServicing} onChange={e => setIncludeServicing(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              Uwzględniaj serwisowanie
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={hookInstallation} onChange={e => setHookInstallation(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              <span className="flex items-center">Hak holowniczy <LinkedIndicator tableName="control_center" isLinked={true} /></span>
            </label>
          </div>
        </div>
      </div>
    </>
  );
}
