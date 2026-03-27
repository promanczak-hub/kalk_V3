import { useState, useRef } from "react";
import { Loader2, Database, ExternalLink, History, X } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
import { API_BASE_URL } from "../../../config/env";
import { apiClient } from '../../../lib/apiClient';
import { supabase } from "../../../lib/supabaseClient";
import { buildCalculationPayload } from "./calculations/payloadBuilder";

interface HistoricalCalculation {
  id: string;
  numer_kalkulacji: string;
  created_at: string;
  cena_netto: number;
}

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
  const [phase, setPhase] = useState<'idle' | 'saving' | 'calculating' | 'done'>('idle');
  const isCreateBlocked = Boolean(calculationBlockReason);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<HistoricalCalculation[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  // Phase-based progress mapping (CSS transition handles smooth animation)
  const PHASE_PROGRESS: Record<string, number> = {
    idle: 0,
    saving: 30,
    calculating: 70,
    done: 100,
  };
  const progress = PHASE_PROGRESS[phase] ?? 0;

  const loadHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const res = await apiClient.fetch(`/api/kalkulacje/vehicle/${vehicle.id}`);
      if (!res.ok) throw new Error("Błąd pobierania historii");
      const data = await res.json();
      setHistoryItems(data);
    } catch (err) {
      console.error(err);
      alert("Nie udało się pobrać historii kalkulacji.");
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleOpenHistory = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsHistoryModalOpen(true);
    loadHistory();
  };

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
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Kalkulacja przerwana');
      } else {
        console.error("B\u0142\u0105d tworzenia kalkulacji:", err);
        alert("Nie uda\u0142o si\u0119 utworzy\u0107 kalkulacji. Sprawd\u017A logi serwera.");
      }
    } finally {
      setIsCreating(false);
      setPhase('idle');
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
      const baseUrl = API_BASE_URL;
      const rawText = JSON.stringify(vehicle.synthesis_data || {});
      
      const brochurePromise = apiClient.fetch(`${baseUrl}/api/parse-offer/extract-brochure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText }),
      }).then(r => {
        if (!r.ok) throw new Error("Brochure extraction failed");
        return r.json();
      });

      const isPdfUrl = vehicle.raw_pdf_url && /\.pdf$/i.test(vehicle.raw_pdf_url);
      const imagesPromise = isPdfUrl
        ? apiClient.fetch(`${baseUrl}/api/parse-offer/extract-images`, {
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
        throw new Error("Nie uda\u0142o si\u0119 wygenerowa\u0107 broszury z AI.");
      }

      if (imagesResult.status === 'fulfilled') {
        setBrochureImages(imagesResult.value.images || []);
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
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
           <div 
             className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full" 
             style={{ width: `${progress}%`, transition: phase === 'done' ? 'width 0.3s ease-out' : 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1)' }} 
           />
        </div>
      )}
      {isCreateBlocked && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {calculationBlockReason}
        </div>
      )}
      <div className="flex justify-end items-center gap-3">
      <button
        onClick={handleOpenHistory}
        disabled={isSavingSetup || isCreating || isCreateBlocked}
        className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-orange-50 border border-orange-100 text-orange-700 hover:bg-orange-100 hover:border-orange-200 hover:shadow-sm transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <History className="w-3.5 h-3.5 mr-2" />
        Historia
      </button>

      <button
        onClick={handleCreateCalculation}
        disabled={isSavingSetup || isCreateBlocked}
        title={isCreateBlocked ? (calculationBlockReason ?? undefined) : undefined}
        className={cn(
          "flex items-center text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed",
          isCreating 
            ? "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100" 
            : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md"
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
         <span className="absolute -top-3 right-0 bg-emerald-500 text-white text-[10px] px-2 py-0.5 rounded-full shadow-sm font-bold border border-white z-10">
           ZAŁADOWANO: {activeKalkulacjaNumer.split('/').pop()}
         </span>
      )}



      <button
        onClick={handleGenerateBrochure}
        disabled={isGeneratingBrochure}
        className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-700 hover:bg-indigo-100 hover:border-indigo-200 hover:shadow-sm transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
          const event = new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } });
          window.dispatchEvent(event);
        }}
        className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-red-50 border border-red-100 text-red-600 hover:bg-red-100 hover:border-red-200 hover:shadow-sm transition-all shadow-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
        {"Usuń"}
      </button>
      </div>

      {/* MODAL: Historia kalkulacji dla pojazdu */}
      {isHistoryModalOpen && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4"
          onClick={(e) => { e.stopPropagation(); setIsHistoryModalOpen(false); }}
        >
          <div 
            className="w-full max-w-2xl bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50/80">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-blue-600" />
                <h3 className="font-semibold text-slate-800">Historia Kalkulacji dla tego pojazdu</h3>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); setIsHistoryModalOpen(false); }}
                className="p-1 hover:bg-slate-200 rounded-lg transition-colors text-slate-500"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1 bg-slate-50/30">
              {isHistoryLoading ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                  <span className="ml-3 text-sm text-slate-500">Pobieranie historii...</span>
                </div>
              ) : historyItems.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-sm">
                  Brak wcześniejszych kalkulacji dla tego pojazdu.
                </div>
              ) : (
                <div className="space-y-2">
                  {historyItems.map((item) => (
                    <div 
                      key={item.id} 
                      className="flex items-center justify-between p-3 rounded-lg border border-slate-200 bg-white hover:bg-blue-50 hover:border-blue-200 transition-colors cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        // Po wybraniu, ładujemy tę kalkulację i zamykamy modal
                        onCalculationCreated(item.id, item.numer_kalkulacji);
                        setIsHistoryModalOpen(false);
                      }}
                    >
                      <div>
                        <div className="font-semibold text-sm text-slate-800">{item.numer_kalkulacji}</div>
                        <div className="text-xs text-slate-500 mt-1">
                          Utworzono: {new Date(item.created_at).toLocaleString("pl-PL")}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-sm text-slate-800">
                           {item.cena_netto ? `${item.cena_netto.toLocaleString('pl-PL')} PLN` : '-'}
                        </div>
                        <div className="text-xs text-blue-600 font-medium">Wczytaj &rarr;</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

