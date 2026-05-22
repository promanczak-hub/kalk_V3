import { Banknote, CircleDot, AlertTriangle } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
export interface ExtractedServiceOption {
  name: string;
  net_price: number;
  description_or_components?: string[];
  effects?: Record<string, unknown> | null;
}
import { LinkedIndicator } from "./LinkedIndicator";
import { useMemo, useState } from "react";
import type { DiscountAlert } from "../../hooks/useDiscountAlerts";
import { AccordionCard } from "./AccordionCard";

interface VehicleFinancialOptionsProps {
  vehicle: FleetVehicleView;
  // Prices
  totalCatalogPriceNet: number;
  activeFinalPriceNet: number;
  dynamicTotalOptionsPrice: number;
  discountableOptionsTotal: number;
  nonDiscountableOptionsTotal: number;
  serviceOptionsTotal: number;
  // Catalog base price (always netto) — read-only here; edycja w sekcji Opcje Fabryczne.
  catalogBasePriceNet: number;
  // Other derived
  isDealerOffer: boolean;
  offerDiscountPercentage: number;
  suggestedDiscountPct: number;
  activeDiscountPct: number;

  handleServiceOptionExtracted?: (option: ExtractedServiceOption) => void;
  // Financial parameters
  wiborPct: number;
  setWiborPct: (val: number) => void;
  marginPct: number;
  setMarginPct: (val: number) => void;
  pricingMarginPct: number;
  setPricingMarginPct: (val: number) => void;
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
  includeTires: boolean;
  setIncludeTires: (val: boolean) => void;
  hookInstallation: boolean;
  setHookInstallation: (val: boolean) => void;
  // Tire parameters
  tireClass: string;
  setTireClass: (val: string) => void;
  tireCountMode: string;
  setTireCountMode: (val: string) => void;
  tireCostCorrectionEnabled: boolean;
  setTireCostCorrectionEnabled: (val: boolean) => void;
  tireCostCorrectionMap: Record<string, number>;
  setTireCostCorrectionMap: (val: Record<string, number>) => void;
  rimDiameter: number | null;
  setRimDiameter: (val: number | null) => void;
  // Service cost type
  serviceCostType: "ASO" | "nonASO";
  setServiceCostType: (val: "ASO" | "nonASO") => void;
  // Vehicle vintage & paint
  vehicleVintage: "current" | "previous";
  setVehicleVintage: (val: "current" | "previous") => void;
  paintCategoryId: number | null;
  setPaintCategoryId: (val: number) => void;
  paintTypes?: { id: number; name: string }[];
  // Faza A - nowe pola wpływające na kalkulację
  // Pakiet serwisowy: state w netto; UI prezentuje brutto (V1-parity).
  // manualWrCorrection usunięty z propsów — globalna korekta WR przeniesiona w pełni do per-matrix
  // override w CellDetail.tsx; pole "Pakiet serwisowy — nazwa" usunięte (V1 nie ma odpowiednika).
  pakietSerwisowy: number;
  setPakietSerwisowy: (val: number) => void;
  odkupOpon: boolean;
  setOdkupOpon: (val: boolean) => void;
  // Uwagi (free text, searchable in main search bar)
  uwagi: string;
  setUwagi: (val: string) => void;
  isMetalicAutoDetected: boolean;
  hookAutoDetected: boolean;
  vintageAutoDetected: boolean;
  // Price context
  activeFinalPriceForDeposit: number;
  crossCardAlerts?: DiscountAlert[];
  // Live param preview
  paramPreview?: {
    service: { found: boolean; rate_per_km: number; type: string; power_band?: string; base_rate?: number; m_brand?: number; m_fuel?: number; m_drive?: number; m_gearbox?: number; total_multiplier?: number; };
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
    vehicle, activeFinalPriceNet,
    catalogBasePriceNet,
    isDealerOffer, offerDiscountPercentage, suggestedDiscountPct, activeDiscountPct,
    discountableOptionsTotal, nonDiscountableOptionsTotal, serviceOptionsTotal,
    wiborPct, setWiborPct, marginPct, setMarginPct, pricingMarginPct, setPricingMarginPct,
    initialDepositPct, setInitialDepositPct, otherServiceCosts, setOtherServiceCosts,
    expressPaysInsurance, setExpressPaysInsurance, replacementCar, setReplacementCar,
    gpsRequired, setGpsRequired, includeServicing, setIncludeServicing,
    includeTires, setIncludeTires,
    hookInstallation, setHookInstallation,
    tireClass, setTireClass, tireCountMode, setTireCountMode,
    tireCostCorrectionEnabled, setTireCostCorrectionEnabled,
    tireCostCorrectionMap, setTireCostCorrectionMap,
    rimDiameter, setRimDiameter,
    serviceCostType, setServiceCostType,
    vehicleVintage, setVehicleVintage,
    paintCategoryId, setPaintCategoryId, paintTypes, isMetalicAutoDetected,
    hookAutoDetected, vintageAutoDetected,
    activeFinalPriceForDeposit,
    paramPreview,
    controlCenter,
    totalCatalogPriceNet,
    // Faza A — nowe pola
    pakietSerwisowy, setPakietSerwisowy,
    odkupOpon, setOdkupOpon,
    uwagi, setUwagi,
  } = props;

  const crossCardAlerts = props.crossCardAlerts ?? [];

  const [depositMode, setDepositMode] = useState<"%" | "PLN">("%");
  // Pakiet serwisowy: state trzyma netto, UI prezentuje brutto (V1-parity: V1 dzieli wartość przez VAT 1.23 przed użyciem).
  const pakietSerwisowyBrutto = Math.round(pakietSerwisowy * 1.23);

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
  // Priority: card_summary._price_domain > card_summary.price_domain > base_price string fallback
  const cardSummary = vehicle.synthesis_data?.card_summary as Record<string, unknown> | undefined;
  const detectedPriceDomain = (cardSummary?._price_domain as string) || (cardSummary?.price_domain as string) || "unknown";
  const isSourceNetto = detectedPriceDomain === "netto"
    || (detectedPriceDomain === "unknown" && (vehicle.base_price?.toLowerCase().includes("netto") ?? false));
  const toNetto = (val: number) => isSourceNetto ? val : val / 1.23;
  const toBrutto = (val: number) => isSourceNetto ? val * 1.23 : val;

  // basePriceNum in source domain derived from editable catalogBasePriceNet
  const basePriceNum = isSourceNetto
    ? catalogBasePriceNet
    : Math.round(catalogBasePriceNet * 1.23);

  return (
    <>
      {/* --- Analiza Finansowa --- */}
      <AccordionCard
        id={`financial-analysis-${vehicle.id}`}
        title="Analiza Finansowa"
        icon={<Banknote className="w-4 h-4 text-emerald-600" />}
        defaultOpen={true}
        className="mb-4"
      >
        <div className="space-y-5">


          {/* Discount alerts */}
          {(isDealerOffer && suggestedDiscountPct > 0 && offerDiscountPercentage > suggestedDiscountPct || crossCardAlerts.length > 0) && (
            <div className="flex flex-col gap-2">
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
          )}

          {/* Rozkład ceny table */}
          <div>
            <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
              Rozkład ceny
            </h5>
            <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
              <colgroup>
                <col style={{ width: "34%" }} />
                <col style={{ width: "33%" }} />
                <col style={{ width: "33%" }} />
              </colgroup>
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-1.5 pr-2 text-left text-[10px] font-bold uppercase tracking-wider text-slate-400">Pozycja</th>
                  <th className="py-1.5 px-2 text-right text-[10px] font-bold uppercase tracking-wider text-slate-400">Netto</th>
                  <th className="py-1.5 pl-2 text-right text-[10px] font-bold uppercase tracking-wider text-slate-400">Brutto</th>
                </tr>
              </thead>
              <tbody>
                {/* Cena bazowa (katalogowa) — read-only; edycja w sekcji Opcje Fabryczne */}
                <tr className="border-b border-slate-100">
                  <td className="py-2.5 pr-2 text-xs text-slate-500">Cena bazowa katalogowa</td>
                  <td className="py-2.5 text-right tabular-nums text-sm text-slate-400">{fmtPLN(catalogBasePriceNet)}</td>
                  <td className="py-2.5 text-right tabular-nums text-sm font-medium text-slate-700">{fmtPLN(catalogBasePriceNet * 1.23)}</td>
                </tr>

                {/* Opcje rabatowane — bezpośrednio pod ceną bazową */}
                {discountableOptionsTotal > 0 && (
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 text-xs text-slate-500">Opcje rabatowane</td>
                    <td className="py-2.5 text-right tabular-nums text-sm text-slate-400">{fmtPLN(discountableOptionsTotal)}</td>
                    <td className="py-2.5 text-right tabular-nums text-sm font-medium text-slate-700">{fmtPLN(discountableOptionsTotal * 1.23)}</td>
                  </tr>
                )}

                {/* Opcje fabryczne nierabatowane — wciąż część katalogu, dlatego przed sumą */}
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

                {/* Suma przed rabatem (Katalog + Opcje rabatowane + nierabatowane). Serwisy idą NIŻEJ — nie wchodzą do bazy rabatu. */}
                <tr className="border-b border-slate-200 bg-slate-50/30">
                  <td className="py-2.5 pr-2 text-xs font-bold text-slate-600">Suma przed rabatem</td>
                  <td className="py-2.5 px-2 text-right tabular-nums text-sm font-bold text-slate-600">
                    {fmtPLN(totalCatalogPriceNet)}
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-sm font-bold text-slate-800">
                    {fmtPLN(totalCatalogPriceNet * 1.23)}
                  </td>
                </tr>

                {/* Rabat */}
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

                {/* Usługi serwisowe — poza bazą rabatu, dodawane po rabacie do ceny końcowej */}
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
                  <td className="py-2.5 text-right tabular-nums text-sm font-semibold text-slate-700">{fmtPLN(activeFinalPriceNet)}</td>
                  <td className="py-2.5 text-right tabular-nums text-sm font-semibold text-slate-900">{fmtPLN(activeFinalPriceNet * 1.23)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </AccordionCard>

      {/* Parametry Kalkulacji */}
      <AccordionCard
        id={`calculation-params-${vehicle.id}`}
        title="Parametry Kalkulacji"
        icon={
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
        }
        defaultOpen={true}
        className="mb-4"
      >
        <div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">WIBOR (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={wiborPct} onChange={e => setWiborPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Marża bankowa (%)</label>
              <input type="number" step="0.01" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={marginPct} onChange={e => setMarginPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Marża Sprzedaży LTR (%)</label>
              <input type="number" step="0.1" className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500" value={pricingMarginPct} onChange={e => setPricingMarginPct(parseFloat(e.target.value) || 0)} />
            </div>
            <div className="row-span-2">
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-bold uppercase text-slate-500">Czynsz inicjalny</label>
                <div className="flex border border-slate-200 rounded overflow-hidden">
                  <button 
                    type="button" 
                    onClick={() => setDepositMode("%")}
                    className={cn("px-1.5 py-0.5 text-[9px] font-bold transition-colors", depositMode === "%" ? "bg-slate-100 text-slate-600" : "bg-white text-slate-400 hover:bg-slate-50")}
                  >
                    %
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setDepositMode("PLN")}
                    className={cn("px-1.5 py-0.5 text-[9px] font-bold transition-colors", depositMode === "PLN" ? "bg-slate-100 text-slate-600" : "bg-white text-slate-400 hover:bg-slate-50")}
                  >
                    PLN
                  </button>
                </div>
              </div>
              <div className="flex gap-1.5">
                <input
                  type="number" step={depositMode === "%" ? "0.1" : "100"}
                  className="w-20 text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 font-bold tabular-nums"
                  value={depositMode === "%" ? initialDepositPct : Math.round(depositAmountNet)}
                  onChange={e => {
                    const val = parseFloat(e.target.value) || 0;
                    if (depositMode === "%") {
                      setInitialDepositPct(val);
                    } else {
                      const newPct = activeFinalPriceForDeposit > 0 ? (val / activeFinalPriceForDeposit) * 100 : 0;
                      setInitialDepositPct(parseFloat(newPct.toFixed(2)));
                    }
                  }}
                />
                <div className="flex-1 text-[9px] text-slate-400 flex flex-col justify-center leading-tight">
                  {depositMode === "%" ? (
                    <>
                      <span>= {depositAmountNet.toFixed(0)} PLN netto</span>
                      <span>= {depositAmountGross.toFixed(0)} PLN brutto</span>
                    </>
                  ) : (
                    <>
                      <span>= {initialDepositPct}%</span>
                      <span>= {depositAmountGross.toFixed(0)} PLN brutto</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Faza A: Pakiet serwisowy (brutto, V1-parity) + Odkup opon.
              Korekta WR przeniesiona w pełni do per-matrix override (CellDetail.tsx). */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 pt-3 border-t border-slate-100">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
                Pakiet serwisowy (brutto/kontrakt)
                <span className="ml-1 text-[9px] font-normal text-slate-400 normal-case" title="Dedykowany pakiet serwisowy — całkowity koszt BRUTTO na cały okres kontraktu (V1-parity). Jeśli > 0, zastępuje logikę km-ową. Frontend konwertuje na netto (÷1.23) przed wysłaniem do backendu.">ⓘ</span>
              </label>
              <input
                type="number" step="100"
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 tabular-nums"
                value={pakietSerwisowyBrutto}
                onChange={e => {
                  const brutto = parseFloat(e.target.value) || 0;
                  setPakietSerwisowy(parseFloat((brutto / 1.23).toFixed(2)));
                }}
                placeholder="0"
              />
              {pakietSerwisowy !== 0 && (
                <div className="text-[9px] text-slate-400 mt-0.5">
                  ≈ {pakietSerwisowy.toFixed(0)} PLN netto (V1: brutto ÷ VAT 1.23)
                </div>
              )}
            </div>
            <div className="flex items-end pb-0.5">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900">
                <input
                  type="checkbox"
                  checked={odkupOpon}
                  onChange={e => setOdkupOpon(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5"
                />
                <span className="font-semibold">Odkup opon</span>
                <span className="text-[9px] text-slate-400 normal-case" title="Włącz logikę obniżenia kosztów przez odkup opon na koniec kontraktu (V1-parity: cena z tabeli koszty_opon.odkup_opon po średnicy felgi).">ⓘ</span>
              </label>
            </div>
          </div>

          {/* Uwagi (free text, searchable) */}
          <div className="pt-3 border-t border-slate-100">
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
              Uwagi
              <span className="ml-1 text-[9px] font-normal text-slate-400 normal-case" title="Tekst dowolny. Można wyszukiwać po treści w głównym polu wyszukiwania (Skan wyposażenia).">ⓘ przeszukiwalne</span>
            </label>
            <textarea
              value={uwagi}
              onChange={e => setUwagi(e.target.value)}
              placeholder="Notatki do kalkulacji: warunki, przypomnienia, kontekst klienta itd. Zostaną przeszukane przy filtrowaniu listy pojazdów."
              rows={2}
              className="w-full text-xs p-2 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 resize-y min-h-[40px]"
            />
            {uwagi.trim().length > 0 && (
              <div className="text-[9px] text-emerald-600 mt-0.5 font-semibold">
                ✓ {uwagi.trim().length} znaków — zapis nastąpi przy &laquo;Zapisz Setup&raquo;
              </div>
            )}
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
                <LinkedIndicator tableName="samar_service_costs" isLinked={!!paramPreview?.service?.found} previewValue={paramPreview?.service?.found ? `${paramPreview.service.rate_per_km} PLN/km (${paramPreview.service.type})` : undefined} />
              </label>
              <select
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer font-medium text-slate-700"
                value={serviceCostType}
                onChange={(e) => setServiceCostType(e.target.value as "ASO" | "nonASO")}
              >
                <option value="ASO">ASO (Autoryzowany Serwis)</option>
                <option value="nonASO">Non-ASO (Serwis Niezale┼╝ny)</option>
              </select>
            </div>

            {/* Rocznik Dropdown */}
            <div>
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
              Rocznik pojazdu
                <LinkedIndicator tableName="ltr_admin_korekta_wr_roczniks" isLinked={!!paramPreview?.vintage?.found} previewValue={paramPreview?.vintage?.found ? `${(paramPreview.vintage.correction_pct * 100).toFixed(1)}% (${paramPreview.vintage.label})` : undefined} />
                {vintageAutoDetected && (
                  <span className="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-semibold border border-slate-200" title="Wartość wyodrębniona automatycznie">
                    AUTO
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

            {/* Paint category dropdown */}
            <div>
              <label className="flex items-center text-xs font-bold uppercase text-slate-500 mb-1">
                Kategoria lakieru
                <LinkedIndicator tableName="paint_types" isLinked={!!paramPreview?.color?.found} previewValue={paramPreview?.color?.found ? `${(paramPreview.color.correction_pct * 100).toFixed(1)}% (${paramPreview.color.label})` : undefined} />
                {isMetalicAutoDetected && (
                   <span className="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-semibold border border-slate-200" title="Wartość wyodrębniona automatycznie">
                     AUTO
                   </span>
                 )}
              </label>
              <select
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer font-medium text-slate-700"
                value={paintCategoryId || ""}
                onChange={(e) => setPaintCategoryId(parseInt(e.target.value, 10))}
              >
                {!paintCategoryId && <option value="" disabled>Wybierz lakier...</option>}
                {paintTypes && paintTypes.map(pt => (
                  <option key={pt.id} value={pt.id}>{pt.name}</option>
                ))}
                {(!paintTypes || paintTypes.length === 0) && (
                  <>
                    <option value="1">Lakier zwykły (Solid)</option>
                    <option value="2">Lakier metalizowany (Metallic)</option>
                    <option value="3">Lakier perłowy (Pearl)</option>
                  </>
                )}
              </select>
            </div>
          </div>

          {/* Toggles Row */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-x-6 gap-y-2 pt-3 border-t border-slate-100">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700 hover:text-slate-900 py-1">
              <input type="checkbox" checked={includeTires} onChange={e => setIncludeTires(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5" />
              <span className="font-semibold text-blue-700">Express dolicza opony</span>
            </label>
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
                  <span className="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-semibold border border-slate-200" title="Wartość wyodrębniona automatycznie">
                    AUTO
                  </span>
                )}
              </span>
            </label>
          </div>

          {/* --- Opony (wewnątrz Parametry Kalkulacji) --- */}
          {includeTires && (
            <div className="mt-4 pt-4 border-t border-slate-200 transition-all duration-300 bg-blue-50/30 ring-1 ring-blue-500/20 p-2 rounded-lg relative">
              <div className="flex items-center mb-3">
              <CircleDot className="w-4 h-4 text-emerald-600 mr-2" />
              <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wider">Parametry Opon</h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                  {vehicle.wheels && <span className="text-[10px] text-slate-400 ml-1">z dokumentu: {vehicle.wheels}</span>}
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

              {/* Tire cost correction per-komórka */}
              <div className="col-span-2 md:col-span-4">
                <div className="flex items-center gap-2 mb-2">
                  <input
                    type="checkbox"
                    id={`tire-corr-enabled-${vehicle.id}`}
                    checked={tireCostCorrectionEnabled}
                    onChange={(e) => setTireCostCorrectionEnabled(e.target.checked)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3 w-3"
                  />
                  <label htmlFor={`tire-corr-enabled-${vehicle.id}`} className="text-xs font-bold uppercase text-slate-500 cursor-pointer">
                    Korekta kosztu opon per-komórka (brutto PLN)
                  </label>
                  {tireCostCorrectionEnabled && (
                    <button
                      type="button"
                      onClick={() => {
                        setTireCostCorrectionMap({ ...tireCostCorrectionMap, "48_120000": 0 });
                      }}
                      className="ml-auto flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
                    >
                      + Dodaj korektę
                    </button>
                  )}
                </div>
                {tireCostCorrectionEnabled && Object.keys(tireCostCorrectionMap).length > 0 && (
                  <div className="space-y-1.5 p-2 bg-slate-50 border border-slate-200 rounded-lg">
                    <div className="grid grid-cols-[80px_100px_100px_28px] gap-1.5 text-[9px] font-bold uppercase text-slate-400 px-1">
                      <span>Okres (mies.)</span>
                      <span>Km/rok</span>
                      <span>Kwota brutto</span>
                      <span></span>
                    </div>
                    {Object.entries(tireCostCorrectionMap).map(([key, val]) => {
                      const parts = key.split("_");
                      const months = parseInt(parts[0], 10) || 48;
                      const totalKm = parseInt(parts[1], 10) || 0;
                      const kmPerYear = totalKm > 0 && months > 0 ? Math.round((totalKm / months) * 12) : 0;
                      return (
                        <div key={key} className="grid grid-cols-[80px_100px_100px_28px] gap-1.5 items-center">
                          <select
                            className="text-xs p-1 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 font-medium"
                            value={months}
                            onChange={(e) => {
                              const newMonths = parseInt(e.target.value, 10);
                              const newTotalKm = kmPerYear > 0 ? Math.round((kmPerYear / 12) * newMonths) : totalKm;
                              const newKey = `${newMonths}_${newTotalKm}`;
                              const updated = { ...tireCostCorrectionMap };
                              delete updated[key];
                              updated[newKey] = val;
                              setTireCostCorrectionMap(updated);
                            }}
                          >
                            {[24, 36, 48, 60].map(m => <option key={m} value={m}>{m}</option>)}
                          </select>
                          <input
                            type="number"
                            step="5000"
                            min="0"
                            className="text-xs p-1 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                            value={kmPerYear}
                            onChange={(e) => {
                              const newKmPerYear = parseInt(e.target.value, 10) || 0;
                              const newTotalKm = Math.round((newKmPerYear / 12) * months);
                              const newKey = `${months}_${newTotalKm}`;
                              const updated = { ...tireCostCorrectionMap };
                              delete updated[key];
                              updated[newKey] = val;
                              setTireCostCorrectionMap(updated);
                            }}
                          />
                          <input
                            type="number"
                            step="1"
                            className="text-xs p-1 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                            value={val}
                            onChange={(e) => {
                              setTireCostCorrectionMap({ ...tireCostCorrectionMap, [key]: parseFloat(e.target.value) || 0 });
                            }}
                          />
                          <button
                            type="button"
                            onClick={() => {
                              const updated = { ...tireCostCorrectionMap };
                              delete updated[key];
                              setTireCostCorrectionMap(updated);
                            }}
                            className="flex items-center justify-center h-6 w-6 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors"
                          >
                            ×
                          </button>
                        </div>
                      );
                    })}
                    <p className="text-[9px] text-slate-400 px-1 pt-1">Klucz: mies_totalKm · Backend: kwota ÷ 1.23 → netto</p>
                  </div>
                )}
                {tireCostCorrectionEnabled && Object.keys(tireCostCorrectionMap).length === 0 && (
                  <p className="text-[10px] text-slate-400 italic">Brak korekt — kliknij Dodaj korektę aby ustawić per-komórka.</p>
                )}
              </div>
            </div>
          </div>
          )}
        </div>
      </AccordionCard>
    </>
  );
}
