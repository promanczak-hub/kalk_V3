import { Banknote, Database, Loader2, Wrench, CircleDot, AlertTriangle } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
import { ServiceOptionsManager } from "../../../components/Calculator/ServiceOptionsManager";
import type { ExtractedServiceOption } from "../../../components/Calculator/ServiceOptionsManager";
import { NetGrossInput } from "./NetGrossInput";
import { LinkedIndicator } from "./LinkedIndicator";
import { useMemo } from "react";
import type { DiscountAlert } from "../../hooks/useDiscountAlerts";

interface VehicleFinancialOptionsProps {
  vehicle: FleetVehicleView;
  // Prices
  totalCatalogPrice: number;
  activeFinalPrice: number;
  dynamicTotalOptionsPrice: number;
  discountableOptionsTotal: number;
  nonDiscountableOptionsTotal: number;
  serviceOptionsTotal: number;
  // Discount state
  discountMode: "offer" | "suggested" | "custom";
  setDiscountMode: (mode: "offer" | "suggested" | "custom") => void;
  customDiscountPctRaw: string | number;
  setCustomDiscountPctRaw: (val: string) => void;
  // Other derived
  isDealerOffer: boolean;
  offerDiscountPercentage: number;
  suggestedDiscountPct: number;
  suggestedDiscountConfidence: number;
  activeDiscountPct: number;

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
  rimDiameter: number | null;
  setRimDiameter: (val: number | null) => void;
  // Service cost type
  serviceCostType: "ASO" | "nonASO";
  setServiceCostType: (val: "ASO" | "nonASO") => void;
  // Vehicle vintage & metalic
  vehicleVintage: "current" | "previous";
  setVehicleVintage: (val: "current" | "previous") => void;
  isMetalic: boolean;
  setIsMetalic: (val: boolean) => void;
  isMetalicAutoDetected: boolean;
  hookAutoDetected: boolean;
  vintageAutoDetected: boolean;
  // Czynsz inicjalny netto/brutto
  activeFinalPriceForDeposit: number;
  crossCardAlerts?: DiscountAlert[];
  // Live param preview from backend
  paramPreview?: {
    service: { found: boolean; rate_per_km: number; type: string; power_band: string };
    tires: { found: boolean; set_price_net: number; rim_diameter: number; tire_class: string };
    vintage: { found: boolean; correction_pct: number; label: string };
    color: { found: boolean; correction_pct: number; label: string };
    replacement_car: { found: boolean; daily_rate_net: number; avg_days_year: number };
  } | null;
  controlCenter?: {
    cost_gsm_device: number;
    cost_gsm_installation: number;
    cost_gsm_subscription_monthly: number;
    cost_hook_installation: number;
  } | null;
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
  { value: "3", label: "3 komplety" },
  { value: "3.5", label: "3,5 kompletu" },
  { value: "4", label: "4 komplety" },
  { value: "4.5", label: "4,5 kompletu" },
  { value: "5", label: "5 kompletów" },
  { value: "5.5", label: "5,5 kompletu" },
  { value: "6", label: "6 kompletów" },
  { value: "6.5", label: "6,5 kompletu" },
  { value: "7", label: "7 kompletów" },
  { value: "7.5", label: "7,5 kompletu" },
  { value: "8", label: "8 kompletów" },
];

export function VehicleFinancialOptions(props: VehicleFinancialOptionsProps) {
  const {
    vehicle, totalCatalogPrice, activeFinalPrice, dynamicTotalOptionsPrice,
    discountMode, setDiscountMode, customDiscountPctRaw, setCustomDiscountPctRaw,
    isDealerOffer, offerDiscountPercentage, suggestedDiscountPct, suggestedDiscountConfidence, activeDiscountPct,
    discountableOptionsTotal, nonDiscountableOptionsTotal, serviceOptionsTotal,
    customServiceOptions, handleUpdateServiceOptionName,
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
    rimDiameter, setRimDiameter,
    serviceCostType, setServiceCostType,
    vehicleVintage, setVehicleVintage,
    isMetalic, setIsMetalic, isMetalicAutoDetected,
    hookAutoDetected, vintageAutoDetected,
    activeFinalPriceForDeposit,
    paramPreview,
    controlCenter,
  } = props;

  const crossCardAlerts = props.crossCardAlerts ?? [];

  // Extracted wheel size from AI
  const extractedWheelSize = useMemo(() => {
    const wheels = vehicle.wheels || "";
    const match = wheels.match(/(\d{2})/);
    return match ? parseInt(match[1], 10) : null;
  }, [vehicle.wheels]);

  // Czynsz inicjalny calculated amounts
  const depositAmountNet = activeFinalPriceForDeposit * (initialDepositPct / 100);
  const depositAmountGross = depositAmountNet * 1.23;


  // Helper: format currency for breakdown
  const fmtPLN = (value: number): string => {
    if (value === 0) return "—";
    return value.toLocaleString("pl-PL", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + " PLN";
  };

  // Detect if source prices are netto or brutto
  const isSourceNetto = vehicle.base_price?.toLowerCase().includes("netto") ?? false;
  const toNetto = (val: number) => isSourceNetto ? val : val / 1.23;
  const toBrutto = (val: number) => isSourceNetto ? val * 1.23 : val;

  // Calculate Rozkład ceny rows
  // dynamicTotalOptionsPrice is always netto (sum of price_net), convert to source domain
  const optionsInSourceDomain = isSourceNetto
    ? dynamicTotalOptionsPrice
    : dynamicTotalOptionsPrice * 1.23;
  const basePriceNum = totalCatalogPrice - optionsInSourceDomain;

  return (
    <>
      {/* ═══ Analiza Finansowa ═══ */}
      <div className="border border-slate-200 rounded bg-white mb-8 mt-6">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
          <h4 className="flex items-center text-xs font-semibold uppercase tracking-wider text-slate-500">
            <Banknote className="w-4 h-4 mr-2 text-slate-400" />
            Analiza Finansowa
          </h4>
        </div>

        <div className="p-5 space-y-5">
          {/* Rabat selector — compact inline */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">Rabat:</span>
              <select 
                className="bg-white border border-slate-200 text-slate-700 font-medium text-xs rounded px-2 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none cursor-pointer"
                value={discountMode}
                onChange={(e) => setDiscountMode(e.target.value as "offer" | "suggested" | "custom")}
              >
                <option value="offer">Z oferty ({isDealerOffer ? offerDiscountPercentage : 0}%)</option>
                <option value="suggested" disabled={suggestedDiscountPct === 0}>
                  Suger. BD ({suggestedDiscountPct}%){suggestedDiscountConfidence > 0 ? ` [${suggestedDiscountConfidence}%]` : ''}
                </option>
                <option value="custom">Własny</option>
              </select>
              <div className="flex items-center bg-white rounded shadow-sm border border-slate-200 overflow-hidden">
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
                <span className="text-xs font-bold pr-1.5 py-1 border-l text-slate-400 bg-slate-100 border-slate-200">%</span>
              </div>
            </div>

            {/* Discount alerts */}
            {isDealerOffer && suggestedDiscountPct > 0 && offerDiscountPercentage > suggestedDiscountPct && (
              <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2 text-[11px] text-amber-800 text-left animate-in fade-in duration-300">
                <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-bold">Dealer: {offerDiscountPercentage}%</span> vs BD: {suggestedDiscountPct}%
                  <span className="font-semibold ml-1">(+{(offerDiscountPercentage - suggestedDiscountPct).toFixed(1)} pp.)</span>
                </div>
              </div>
            )}
            {crossCardAlerts.map((alert, idx) => (
              <div key={idx} className="p-2 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2 text-[11px] text-amber-800 text-left animate-in fade-in duration-300">
                <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-bold">Inna oferta: {alert.siblingDiscountPct}%</span> vs obecne {alert.currentDiscountPct}%
                  <span className="font-semibold ml-1">(+{alert.deltaPp} pp.)</span>
                </div>
              </div>
            ))}
          </div>

          {/* Rozkład ceny table */}
          <div>
            <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Rozkład ceny</h5>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-1.5 text-left text-xs font-bold uppercase text-slate-400">Pozycja</th>
                  <th className="py-1.5 text-right text-xs font-bold uppercase text-slate-400">Netto</th>
                  <th className="py-1.5 text-right text-xs font-bold uppercase text-slate-400">Brutto</th>
                </tr>
              </thead>
              <tbody>
                {/* Cena bazowa (katalogowa) */}
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 text-xs text-slate-500">Cena bazowa</td>
                  <td className="py-2.5 text-right tabular-nums text-sm text-slate-400">{basePriceNum > 0 ? fmtPLN(toNetto(basePriceNum)) : "—"}</td>
                  <td className="py-2.5 text-right tabular-nums text-sm font-medium text-slate-700">{basePriceNum > 0 ? fmtPLN(toBrutto(basePriceNum)) : "—"}</td>
                </tr>

                {/* Opcje rabatowane */}
                {discountableOptionsTotal > 0 && (
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 text-xs text-slate-500">Opcje rabatowane</td>
                    <td className="py-2.5 text-right tabular-nums text-sm text-slate-400">{fmtPLN(discountableOptionsTotal)}</td>
                    <td className="py-2.5 text-right tabular-nums text-sm font-medium text-slate-700">{fmtPLN(discountableOptionsTotal * 1.23)}</td>
                  </tr>
                )}

                {/* Rabat — shows after discountable items */}
                {activeDiscountPct > 0 && (
                  <>
                    <tr className="border-b border-slate-100 bg-emerald-50/40">
                      <td className="py-2.5 text-xs font-medium text-emerald-700">
                        Rabat ({activeDiscountPct}%)
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-sm text-emerald-600">
                        ({fmtPLN(toNetto(basePriceNum) * (activeDiscountPct / 100) + discountableOptionsTotal * (activeDiscountPct / 100))})
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-sm font-medium text-emerald-700">
                        ({fmtPLN(toBrutto(basePriceNum) * (activeDiscountPct / 100) + discountableOptionsTotal * 1.23 * (activeDiscountPct / 100))})
                      </td>
                    </tr>

                    {/* Subtotal po rabacie */}
                    <tr className="border-b border-slate-200">
                      <td className="py-2 text-xs font-semibold text-slate-600">Suma po rabacie</td>
                      <td className="py-2 text-right tabular-nums text-sm font-semibold text-slate-600">
                        {fmtPLN((toNetto(basePriceNum) + discountableOptionsTotal) * (1 - activeDiscountPct / 100))}
                      </td>
                      <td className="py-2 text-right tabular-nums text-sm font-semibold text-slate-600">
                        {fmtPLN((toBrutto(basePriceNum) + discountableOptionsTotal * 1.23) * (1 - activeDiscountPct / 100))}
                      </td>
                    </tr>
                  </>
                )}

                {/* Opcje fabryczne nierabatowane */}
                {nonDiscountableOptionsTotal > 0 && (
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 text-xs text-slate-500 flex items-center gap-1.5">
                      <button
                        type="button"
                        className="flex items-center gap-1.5 hover:text-blue-600 transition-colors cursor-pointer group/link"
                        onClick={() => {
                          const el = document.getElementById("factory-options-section");
                          if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                        }}
                        title="Przejdź do sekcji Opcje Fabryczne"
                      >
                        Opcje fabryczne nierabatowane
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-300 group-hover/link:text-blue-500 transition-colors"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
                      </button>
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 uppercase tracking-wider">bez rabatu</span>
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-sm text-slate-400">{fmtPLN(nonDiscountableOptionsTotal)}</td>
                    <td className="py-2.5 text-right tabular-nums text-sm font-medium text-slate-700">{fmtPLN(nonDiscountableOptionsTotal * 1.23)}</td>
                  </tr>
                )}

                {/* Usługi serwisowe (always non-discountable) */}
                {serviceOptionsTotal > 0 && (
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 text-xs text-slate-500">Usługi serwisowe</td>
                    <td className="py-2.5 text-right tabular-nums text-sm text-slate-400">{fmtPLN(serviceOptionsTotal)}</td>
                    <td className="py-2.5 text-right tabular-nums text-sm font-medium text-slate-700">{fmtPLN(serviceOptionsTotal * 1.23)}</td>
                  </tr>
                )}

                {/* Cena końcowa */}
                <tr className="border-t-2 border-slate-300">
                  <td className="py-2.5 text-sm font-semibold text-slate-900">Cena końcowa</td>
                  <td className="py-2.5 text-right tabular-nums text-sm font-semibold text-slate-700">{fmtPLN(toNetto(activeFinalPrice))}</td>
                  <td className="py-2.5 text-right tabular-nums text-sm font-semibold text-slate-900">{fmtPLN(toBrutto(activeFinalPrice))}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
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
                           <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-500 hover:text-slate-700 mr-2 border border-slate-100 px-2 py-1 rounded bg-slate-50/50">
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
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
                Średnica felgi
                <LinkedIndicator tableName="koszty_opon" isLinked={!!(paramPreview?.tires?.found && rimDiameter)} previewValue={paramPreview?.tires?.found ? `${paramPreview.tires.set_price_net} PLN/kpl` : undefined} />
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min="14"
                  max="24"
                  step="1"
                  className={cn(
                    "w-16 text-xs p-1.5 border rounded outline-none focus:ring-1 focus:ring-blue-500 font-semibold",
                    rimDiameter ? "border-slate-200 text-slate-700" : "border-amber-300 text-amber-700 bg-amber-50"
                  )}
                  value={rimDiameter ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    setRimDiameter(val ? parseInt(val, 10) || null : null);
                  }}
                  placeholder={extractedWheelSize ? String(extractedWheelSize) : "—"}
                />
                <span className="text-xs text-slate-400">"</span>
                {vehicle.wheels && <span className="text-[10px] text-slate-400 ml-1">z AI: {vehicle.wheels}</span>}
                {!rimDiameter && <span className="text-[10px] text-amber-600 font-semibold ml-1">⚠ wymagane</span>}
              </div>
            </div>

            {/* Tire class dropdown */}
            <div>
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
                Klasa opon
                <LinkedIndicator tableName="koszty_opon" isLinked={!!paramPreview?.tires?.found} previewValue={paramPreview?.tires?.found ? `${paramPreview.tires.set_price_net} PLN/kpl (${paramPreview.tires.tire_class})` : undefined} />
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
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Liczba kompletów</label>
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
              <label className="flex items-center gap-2 text-xs font-bold uppercase text-slate-500 mb-1">
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
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">WIBOR (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={wiborPct} onChange={e => setWiborPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Marża bankowa (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={marginPct} onChange={e => setMarginPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Wskaźnik amortyzacji (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none bg-slate-50 text-slate-500 cursor-not-allowed" value={depreciationPct} readOnly />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Marża Sprzedaży LTR (%)</label>
              <input type="number" step="0.1" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={pricingMarginPct} onChange={e => setPricingMarginPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Czynsz inicjalny (%)</label>
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
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Inne koszty serwisowania (PLN/mc)</label>
              <input type="number" step="1" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={otherServiceCosts} onChange={e => setOtherServiceCosts(parseFloat(e.target.value) || 0)} />
            </div>

            {/* ASO / nonASO Dropdown */}
            <div>
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
                Rodzaj kosztów serwisu
                <LinkedIndicator tableName="samar_service_costs" isLinked={!!paramPreview?.service?.found} previewValue={paramPreview?.service?.found ? `${paramPreview.service.rate_per_km} PLN/km (${paramPreview.service.type}, ${paramPreview.service.power_band})` : undefined} />
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
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
              Rocznik pojazdu
                <LinkedIndicator tableName="ltr_admin_korekta_wr_roczniks" isLinked={!!paramPreview?.vintage?.found} previewValue={paramPreview?.vintage?.found ? `${(paramPreview.vintage.correction_pct * 100).toFixed(1)}% (${paramPreview.vintage.label})` : undefined} />
                {vintageAutoDetected && (
                  <span className="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 font-semibold ring-1 ring-emerald-200">
                    AI
                  </span>
                )}
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
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
                Lakier metalik
                <LinkedIndicator tableName="paint_types" isLinked={!!paramPreview?.color?.found} previewValue={paramPreview?.color?.found ? `${(paramPreview.color.correction_pct * 100).toFixed(1)}% (${paramPreview.color.label})` : undefined} />
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
              <span className="flex items-center">Samochód zastępczy <LinkedIndicator tableName="replacement_car_rates" isLinked={!!paramPreview?.replacement_car?.found} previewValue={paramPreview?.replacement_car?.found ? `${paramPreview.replacement_car.daily_rate_net} PLN/doba, ${paramPreview.replacement_car.avg_days_year} dni/rok` : undefined} /></span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={gpsRequired} onChange={e => setGpsRequired(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              <span className="flex items-center">GPS wymagane <LinkedIndicator tableName="control_center" isLinked={true} previewValue={controlCenter ? `urz. ${controlCenter.cost_gsm_device} + mont. ${controlCenter.cost_gsm_installation} + ${controlCenter.cost_gsm_subscription_monthly}/mc` : undefined} /></span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={includeServicing} onChange={e => setIncludeServicing(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              Uwzględniaj serwisowanie
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={hookInstallation} onChange={e => setHookInstallation(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              <span className="flex items-center">Hak holowniczy <LinkedIndicator tableName="control_center" isLinked={true} previewValue={controlCenter ? `${controlCenter.cost_hook_installation} PLN` : undefined} />
                {hookAutoDetected && (
                  <span className="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 font-semibold ring-1 ring-emerald-200">
                    AI
                  </span>
                )}
              </span>
            </label>
          </div>
        </div>
      </div>
    </>
  );
}
