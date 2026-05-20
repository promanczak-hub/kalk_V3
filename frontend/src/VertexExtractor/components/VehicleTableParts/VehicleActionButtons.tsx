import { useState, useRef } from "react";
import { Loader2, Database, ExternalLink, X, Download } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
import { API_BASE_URL } from "../../../config/env";
import { apiClient } from '../../../lib/apiClient';
import { supabase } from "../../../lib/supabaseClient";
import { buildCalculationPayload } from "./calculations/payloadBuilder";
import { buildBrochureData, type BrochureData } from "../brochure/buildBrochureData";


interface VehicleActionButtonsProps {
  vehicle: FleetVehicleView;
  isSavingSetup: boolean;
  handleSaveSetup: () => Promise<void>;
  pricingMarginPct: number;
  initialDepositPct: number;
  expressPaysInsurance: boolean;
  replacementCar: boolean;
  gpsRequired: boolean;
  includeServicing: boolean;
  includeTires: boolean;
  hookInstallation: boolean;
  tireClass: string;
  tireCountMode: string;
  tireCostCorrectionEnabled: boolean;
  tireCostCorrectionMap: Record<string, number>;
  rimDiameter: number | null;
  serviceCostType: "ASO" | "nonASO";
  vehicleVintage: "current" | "previous";
  paintCategoryId: number | null;
  activeDiscountPct: number;
  activeFinalPrice: number;
  pakietSerwisowy?: number;
  odkupOpon?: boolean;
  brochureData: BrochureData | null;
  setIsBrochureModalOpen: (val: boolean) => void;
  isGeneratingBrochure: boolean;
  setIsGeneratingBrochure: (val: boolean) => void;
  setBrochureData: (val: BrochureData | null) => void;
  setBrochureImages: (val: string[]) => void;
  handleOpenSavedJson: (id: string, name: string) => void;
  isViewerOpen: boolean;
  setIsViewerOpen: (val: boolean) => void;
  onCalculationCreated: (kalkulacjaId: string, numerKalkulacji: string) => void;
  calculationBlockReason?: string | null;
  priceAudit?: {
    threshold_pln: number;
    ai_base_price_netto: number;
    final_base_price_netto: number;
    delta_pln: number;
    manual_review_required: boolean;
  };
  activeKalkulacjaId?: string | null;
  activeKalkulacjaNumer?: string | null;
}

export function VehicleActionButtons({
  vehicle,
  isSavingSetup,
  handleSaveSetup,
  pricingMarginPct,
  initialDepositPct,
  expressPaysInsurance,
  replacementCar,
  gpsRequired,
  includeServicing,
  includeTires,
  hookInstallation,
  tireClass,
  tireCountMode,
  tireCostCorrectionEnabled,
  tireCostCorrectionMap,
  rimDiameter,
  serviceCostType,
  vehicleVintage,
  paintCategoryId,
  activeDiscountPct,
  activeFinalPrice,
  pakietSerwisowy,
  odkupOpon,
  brochureData,
  setIsBrochureModalOpen,
  isGeneratingBrochure,
  setIsGeneratingBrochure,
  setBrochureData,
  setBrochureImages,
  handleOpenSavedJson,
  isViewerOpen,
  setIsViewerOpen,
  onCalculationCreated,
  calculationBlockReason,
  priceAudit,
  activeKalkulacjaNumer,
}: VehicleActionButtonsProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [phase, setPhase] = useState<'idle' | 'saving' | 'calculating' | 'done'>('idle');
  const isCreateBlocked = Boolean(calculationBlockReason);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  // Phase-based progress mapping (CSS transition handles smooth animation)
  const PHASE_PROGRESS: Record<string, number> = {
    idle: 0,
    saving: 30,
    calculating: 70,
    done: 100,
  };
  const progress = PHASE_PROGRESS[phase] ?? 0;

  const handleCreateCalculation = async (e: React.MouseEvent) => {
    e.stopPropagation();
    
    // Przerwanie, jeśli aktualnie trwa kalkulacja
    if (isCreating) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setIsCreating(false);
      setPhase('idle');
      return;
    }

    if (isCreateBlocked) {
      alert(calculationBlockReason || "Wymagana ręczna weryfikacja danych finansowych przed kalkulacją.");
      return;
    }
    
    setIsCreating(true);
    setPhase('saving');
    abortControllerRef.current = new AbortController();
    
    try {
      await handleSaveSetup();
      setPhase('calculating');
      const baseUrl = API_BASE_URL;
      
      const payload = buildCalculationPayload({
          vehicle,
          wiborPct: null, // Force fallback to DB ControlCenterSettings
          marginPct: null, // Force fallback to DB ControlCenterSettings
          pricingMarginPct,
          initialDepositPct,
          otherServiceCosts: null, // Let backend calculate from Matrix or CC
          expressPaysInsurance,
          replacementCar,
          gpsRequired,
          includeServicing,
          includeTires,
          hookInstallation,
          tireClass,
          tireCountMode,
          tireCostCorrectionEnabled,
          tireCostCorrectionMap,
          rimDiameter,
          serviceCostType,
          vehicleVintage,
          paintCategoryId,
          activeDiscountPct,
          activeFinalPrice,
          pakietSerwisowy,
          odkupOpon,
          priceAudit,
      });

      const resp = await apiClient.fetch(`${baseUrl}/api/kalkulacje`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({ stan_json: payload }),
      });
      
      if (!resp.ok) throw new Error("Błąd przy tworzeniu kalkulacji");
      const data = await resp.json();
      const numerKalkulacji = data.numer_kalkulacji || `ID: ${data.id}`;

      // Asynchronous polling for celery task completion
      let isReady = false;
      let attempts = 0;
      while (!isReady && attempts < 15) { // max 30 seconds
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 2000));
        if (abortControllerRef.current.signal.aborted) break;
        
        // Wait for matrix cache to be populated for THIS kalkulacja_id
        const { count, error } = await supabase
           .from("vehicle_matrix_cache")
           .select("*", { count: "exact", head: true })
           .eq("kalkulacja_id", data.id);
           
        if (!error && count && count > 0) {
            isReady = true;
        } else {
            // Also check if Celery job for this vehicle failed
            const { data: jobData } = await supabase
               .from("calculation_jobs")
               .select("status, error_detail")
               .eq("vehicle_id", vehicle.id)
               .order("queued_at", { ascending: false })
               .limit(1)
               .maybeSingle();
            if (jobData?.status === "failed") {
                throw new Error(jobData.error_detail || "Błąd podczas przeliczania w Celery.");
            }
        }
      }

      onCalculationCreated(data.id, numerKalkulacji);
      setPhase('done');
      // Brief visual confirmation before clearing
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Kalkulacja przerwana
      } else {
        console.error("B\u0142\u0105d tworzenia kalkulacji:", err);
        alert("Nie uda\u0142o si\u0119 utworzy\u0107 kalkulacji. Sprawd\u017A logi serwera.");
      }
    } finally {
      setIsCreating(false);
      setPhase('idle');
    }
  };

  const handleDownloadPdf = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!vehicle.raw_pdf_url) return;
    setIsDownloading(true);
    try {
      const res = await fetch(vehicle.raw_pdf_url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const docId = activeKalkulacjaNumer?.split('/').pop() ?? vehicle.id;
      const safe = (s?: string | null) => (s ?? '').replace(/[^a-zA-Z0-9_.-]+/g, '_').replace(/^_+|_+$/g, '');
      const filename = [safe(docId), safe(vehicle.brand), safe(vehicle.model)]
        .filter(Boolean).join('_') + '.pdf';
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('[downloadPdf] failed, fallback to open', err);
      window.open(vehicle.raw_pdf_url, '_blank', 'noopener,noreferrer');
    } finally {
      setIsDownloading(false);
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
      // Build the brochure client-side from the already-normalized vehicle row
      // (fleet_management_view + synthesis_data). RAW values, no LLM round-trip.
      setBrochureData(buildBrochureData(vehicle));

      // Best-effort: pull embedded photos from the original PDF (optional).
      const isPdfUrl = vehicle.raw_pdf_url && /\.pdf$/i.test(vehicle.raw_pdf_url);
      if (isPdfUrl) {
        try {
          const r = await apiClient.fetch(`${API_BASE_URL}/api/parse-offer/extract-images`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pdf_url: vehicle.raw_pdf_url }),
          });
          if (r.ok) {
            const imgs = await r.json();
            setBrochureImages(imgs.images || []);
          }
        } catch {
          // Images are optional \u2014 proceed without them.
        }
      }

      setIsBrochureModalOpen(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Wyst\u0105pi\u0142 nieznany b\u0142\u0105d podczas \u0142adowania broszury");
    } finally {
      setIsGeneratingBrochure(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-2 relative">
      {isCreating && (
        <div className="w-full h-1 bg-slate-200 rounded-full overflow-hidden">
           <div
             className="h-full bg-blue-600 rounded-full"
             style={{ width: `${progress}%`, transition: phase === 'done' ? 'width 0.3s ease-out' : 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
           />
        </div>
      )}
      {isCreateBlocked && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {calculationBlockReason}
        </div>
      )}
      <div className="flex justify-end items-center gap-3">

      <button
        onClick={handleCreateCalculation}
        disabled={isSavingSetup || isCreateBlocked}
        title={isCreateBlocked ? (calculationBlockReason ?? undefined) : undefined}
        className={cn(
          "inline-flex items-center text-xs font-medium px-4 py-2 rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed",
          isCreating
            ? "bg-white text-red-600 border border-red-300 hover:bg-red-50 hover:border-red-500"
            : "bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow"
        )}
      >
        {isSavingSetup ? (
          <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
        ) : isCreating ? (
          <X className="w-3.5 h-3.5 mr-2" />
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
        )}
        {isSavingSetup
          ? "Zapisywanie setupu..."
          : isCreating
            ? "Przerwij"
            : activeKalkulacjaNumer
              ? "Nowa kalkulacja"
              : "Zrób kalkulację"}
      </button>

      {activeKalkulacjaNumer && !isCreating && (
         <span className="absolute -top-3 right-0 bg-emerald-600 text-white text-[10px] px-2 py-0.5 rounded-full font-semibold shadow-sm z-10">
           ZAŁADOWANO: {activeKalkulacjaNumer.split('/').pop()}
         </span>
      )}



      <button
        onClick={handleGenerateBrochure}
        disabled={isGeneratingBrochure}
        className="inline-flex items-center text-xs font-medium px-4 py-2 rounded-md bg-white border border-slate-300 text-slate-700 hover:bg-indigo-50 hover:border-indigo-400 hover:text-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isGeneratingBrochure ? (
          <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin text-indigo-700" />
        ) : (
          <span className="mr-2 text-base leading-none">&#128196;</span>
        )}
        {isGeneratingBrochure ? "Inicjalizacja LLM..." : "Draft Broszury"}
      </button>

      <button
        onClick={(e) => {
          e.stopPropagation();
          handleOpenSavedJson(vehicle.id, `${vehicle.brand} ${vehicle.model}`);
        }}
        className="inline-flex items-center text-xs font-medium px-4 py-2 rounded-md bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-colors"
      >
        <Database className="w-3.5 h-3.5 mr-2" />
        Dane JSON
      </button>

      {vehicle.raw_pdf_url && (
        <>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsViewerOpen(!isViewerOpen);
            }}
            className={cn(
              "inline-flex items-center text-xs font-medium px-4 py-2 rounded-md transition-colors border",
              isViewerOpen
                ? "bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200"
                : "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100 hover:border-blue-400"
            )}
          >
            <ExternalLink className="w-3.5 h-3.5 mr-2" />
            {isViewerOpen ? "Zwiń dokument" : "Otwórz dokument"}
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            className="inline-flex items-center text-xs font-medium px-4 py-2 rounded-md bg-white border border-slate-300 text-slate-700 hover:bg-emerald-50 hover:border-emerald-400 hover:text-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Pobierz oryginalny PDF na dysk"
          >
            {isDownloading
              ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
              : <Download className="w-3.5 h-3.5 mr-2" />}
            {isDownloading ? "Pobieranie..." : "Pobierz PDF"}
          </button>
        </>
      )}

      <button
        onClick={(e) => {
          e.stopPropagation();
          const event = new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } });
          window.dispatchEvent(event);
        }}
        className="inline-flex items-center text-xs font-medium px-4 py-2 rounded-md bg-white border border-red-200 text-red-600 hover:bg-red-50 hover:border-red-400 transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
      </button>
      </div>
    </div>
  );
}

