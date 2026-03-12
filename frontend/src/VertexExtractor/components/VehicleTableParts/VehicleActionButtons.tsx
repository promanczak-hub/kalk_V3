import { useState } from "react";
import { Loader2, Wand2, Database, ExternalLink, FileCode } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
import { API_BASE_URL } from "../../../config/env";

interface VehicleActionButtonsProps {
  vehicle: FleetVehicleView;
  isSavingSetup: boolean;
  handleSaveSetup: () => Promise<void>;
  wiborPct: number;
  marginPct: number;
  pricingMarginPct: number;
  initialDepositPct: number;
  otherServiceCosts: number;
  expressPaysInsurance: boolean;
  replacementCar: boolean;
  gpsRequired: boolean;
  includeServicing: boolean;
  hookInstallation: boolean;
  tireClass: string;
  tireCountMode: string;
  tireCostCorrectionEnabled: boolean;
  tireCostCorrection: number;
  rimDiameter: number | null;
  serviceCostType: "ASO" | "nonASO";
  vehicleVintage: "current" | "previous";
  isMetalic: boolean;
  activeDiscountPct: number;
  activeFinalPrice: number;
  isOverrideModalOpen: boolean;
  setIsOverrideModalOpen: (val: boolean) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  brochureData: any;
  setIsBrochureModalOpen: (val: boolean) => void;
  isGeneratingBrochure: boolean;
  setIsGeneratingBrochure: (val: boolean) => void;
  setBrochureData: (val: any) => void;
  setBrochureImages: (val: string[]) => void;
  handleOpenSavedJson: (id: string, name: string) => void;
  isViewerOpen: boolean;
  setIsViewerOpen: (val: boolean) => void;
  isMarkdownOpen: boolean;
  setIsMarkdownOpen: (val: boolean) => void;
  onCalculationCreated: (kalkulacjaId: string, numerKalkulacji: string) => void;
}

export function VehicleActionButtons({
  vehicle,
  isSavingSetup,
  handleSaveSetup,
  wiborPct,
  marginPct,
  pricingMarginPct,
  initialDepositPct,
  otherServiceCosts,
  expressPaysInsurance,
  replacementCar,
  gpsRequired,
  includeServicing,
  hookInstallation,
  tireClass,
  tireCountMode,
  tireCostCorrectionEnabled,
  tireCostCorrection,
  rimDiameter,
  serviceCostType,
  vehicleVintage,
  isMetalic,
  activeDiscountPct,
  activeFinalPrice,
  isOverrideModalOpen,
  setIsOverrideModalOpen,
  brochureData,
  setIsBrochureModalOpen,
  isGeneratingBrochure,
  setIsGeneratingBrochure,
  setBrochureData,
  setBrochureImages,
  handleOpenSavedJson,
  isViewerOpen,
  setIsViewerOpen,
  setIsMarkdownOpen,
  onCalculationCreated,
}: VehicleActionButtonsProps) {
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateCalculation = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsCreating(true);
    try {
      await handleSaveSetup();
      const baseUrl = API_BASE_URL || "";
      const resp = await fetch(`${baseUrl}/api/kalkulacje`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stan_json: {
            ...(vehicle.synthesis_data || {}),
            vehicle_id: vehicle.id,
            brand: vehicle.brand || "",
            model: vehicle.model || "",
            financial_params: {
              wibor_pct: wiborPct,
              margin_pct: marginPct,
              pricing_margin_pct: pricingMarginPct,
              depreciation_pct: null,
              initial_deposit_pct: initialDepositPct,
              other_service_costs: otherServiceCosts,
            },
            toggles: {
              express_pays_insurance: expressPaysInsurance,
              replacement_car: replacementCar,
              gps_required: gpsRequired,
              include_servicing: includeServicing,
              hook_installation: hookInstallation,
            },
            tire_params: {
              tire_class: tireClass,
              tire_count_mode: tireCountMode,
              tire_cost_correction_enabled: tireCostCorrectionEnabled,
              tire_cost_correction: tireCostCorrection,
              rim_diameter: rimDiameter,
            },
            service_cost_type: serviceCostType,
            vehicle_vintage: vehicleVintage,
            is_metalic: isMetalic,
            discount: {
              active_discount_pct: activeDiscountPct,
              active_final_price: activeFinalPrice,
            },
          }
        }),
      });
      
      if (!resp.ok) throw new Error("Błąd przy tworzeniu kalkulacji");
      const data = await resp.json();
      const numerKalkulacji = data.numer_kalkulacji || `ID: ${data.id}`;

      onCalculationCreated(data.id, numerKalkulacji);
    } catch (err) {
      console.error("Błąd tworzenia kalkulacji:", err);
      alert("Nie udało się utworzyć kalkulacji. Sprawdź logi serwera.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleGenerateBrochure = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (brochureData) {
      setIsBrochureModalOpen(true);
      return;
    }
    setIsGeneratingBrochure(true);
    try {
      const baseUrl = API_BASE_URL || "";
      const rawText = JSON.stringify(vehicle.synthesis_data || {});
      
      const brochurePromise = fetch(`${baseUrl}/api/parse-offer/extract-brochure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText }),
      }).then(r => {
        if (!r.ok) throw new Error("Brochure extraction failed");
        return r.json();
      });

      const isPdfUrl = vehicle.raw_pdf_url && /\.pdf$/i.test(vehicle.raw_pdf_url);
      const imagesPromise = isPdfUrl
        ? fetch(`${baseUrl}/api/parse-offer/extract-images`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pdf_url: vehicle.raw_pdf_url }),
          }).then(r => {
            if (!r.ok) throw new Error("Image extraction failed");
            return r.json();
          })
        : Promise.resolve({ images: [] });

      const [brochureResult, imagesResult] = await Promise.allSettled([brochurePromise, imagesPromise]);

      if (brochureResult.status === 'fulfilled') {
        setBrochureData(brochureResult.value);
      } else {
        throw new Error("Nie udało się wygenerować broszury z AI.");
      }

      if (imagesResult.status === 'fulfilled') {
        setBrochureImages(imagesResult.value.images || []);
      }

      setIsBrochureModalOpen(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Wystąpił nieznany błąd podczas ładowania broszury");
    } finally {
      setIsGeneratingBrochure(false);
    }
  };

  return (
    <div className="flex justify-end items-center gap-3">
      <button
        onClick={handleCreateCalculation}
        disabled={isSavingSetup || isCreating}
        className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSavingSetup || isCreating ? (
          <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
        )}
        {isSavingSetup
          ? "Zapisywanie setupu..."
          : isCreating
            ? "Kalkulowanie..."
            : "Zrób kalkulację"}
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
        onClick={handleGenerateBrochure}
        disabled={isGeneratingBrochure}
        className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-700 hover:bg-indigo-100 hover:border-indigo-200 hover:shadow-sm transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isGeneratingBrochure ? (
          <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin text-indigo-700" />
        ) : (
          <span className="mr-2 text-base leading-none">📄</span>
        )}
        {isGeneratingBrochure ? "Inicjalizacja LLM..." : "Draft Broszury"}
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
        <>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsMarkdownOpen(true);
            }}
            className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-700 hover:bg-indigo-100 hover:border-indigo-200 hover:shadow-sm transition-all shadow-sm"
          >
            <FileCode className="w-3.5 h-3.5 mr-2" />
            Podgląd MD
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsViewerOpen(!isViewerOpen);
            }}
            className={cn(
              "flex items-center text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-sm border",
              isViewerOpen 
                ? "bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200 hover:border-slate-300"
                : "bg-blue-50 border-blue-100 text-blue-700 hover:bg-blue-100 hover:border-blue-200"
            )}
          >
            <ExternalLink className="w-3.5 h-3.5 mr-2" />
            {isViewerOpen ? "Zwiń dokument" : "Otwórz dokument"}
          </button>
        </>
      )}

      <button
        onClick={(e) => {
          e.stopPropagation();
          if (window.confirm("Czy na pewno chcesz usunąć tę plakietkę? Istniejące kalkulacje na jej bazie nie zostaną usunięte.")) {
            const event = new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } });
            window.dispatchEvent(event);
          }
        }}
        className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-red-50 border border-red-100 text-red-600 hover:bg-red-100 hover:border-red-200 hover:shadow-sm transition-all shadow-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
        Usuń
      </button>
    </div>
  );
}
