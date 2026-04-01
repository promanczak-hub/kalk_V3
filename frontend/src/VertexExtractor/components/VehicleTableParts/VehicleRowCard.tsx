import { useState, useEffect, useCallback, useRef } from "react";
import { Loader2, X, AlertTriangle } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
import { parsePriceToNumber } from "./PriceDualFormat";
import { VehicleBaseInfo } from "./VehicleBaseInfo";
import type { MappedData } from "./VehicleBaseInfo";
import { VehicleFinancialOptions } from "./VehicleFinancialOptions";
import BrochureBuilderModal from "../brochure/BrochureBuilderModal";
import { VehicleSummaryCard } from "./VehicleSummaryCard";
import { VehicleEquipmentCard } from "./VehicleEquipmentCard";
import { VehicleFeaturesCard } from "./VehicleFeaturesCard";
import type { DiscountAlert } from "../../hooks/useDiscountAlerts";
import { supabase } from "../../../lib/supabaseClient";
import { apiClient } from '../../../lib/apiClient';
import type { ControlCenterSettings } from "../../../types";

// Custom Hooks
import { useVehicleFinancing } from "../../hooks/useVehicleFinancing";
import { useVehicleDataSync } from "../../hooks/useVehicleDataSync";
import { useVehicleReadiness } from "../../hooks/useVehicleReadiness";
import { useVehicleParamPreview } from "../../hooks/useVehicleParamPreview";
import { useVehicleOptionsManager } from "../../hooks/useVehicleOptionsManager";
import { useVehicleMetaManager } from "../../hooks/useVehicleMetaManager";
import { useVehiclePricingManager } from "../../hooks/useVehiclePricingManager";
import { queuePreloadVehicleFeatures } from "../../hooks/useVehicleFeaturesCache";

// Extracted UI Components
import { VehicleActionButtons } from "./VehicleActionButtons";

import { PDFViewerFrame } from "./PDFViewerFrame";
import { VehicleRowCalculations } from "./VehicleRowCalculations";

// Static lists sourced from DB (samar_classes & engines tables) - updated: 2026-03-18
const ALL_SAMAR_CLASSES: string[] = [
  "Autobusy - AUTOBUSY",
  "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE",
  "Kombivany - H KOMBI-VANY",
  "Lekkie dostawcze - KOMBI VAN",
  "Lekkie dostawcze - VAN",
  "Minibusy - I MINIBUSY",
  "Pick-up - PICK-UP",
  "Podstawowa - A MINI",
  "Podstawowa - B MAŁE",
  "Podstawowa - C NIŻSZA ŚREDNIA",
  "Podstawowa - D ŚREDNIA",
  "Podstawowa - E WYŻSZA",
  "Podstawowa - F LUKSUSOWE",
  "Podstawowa - G SUPER LUKSUSOWE",
  "Sportowo-rekreacyjne - A MINI",
  "Sportowo-rekreacyjne - B MAŁE",
  "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA",
  "Sportowo-rekreacyjne - D ŚREDNIA",
  "Sportowo-rekreacyjne - E WYŻSZA",
  "Sportowo-rekreacyjne - F LUKSUSOWE",
  "Sportowo-rekreacyjne - G SUPER LUKSUSOWE",
  "Średnie dostawcze - ŚREDNIE DOSTAWCZE",
  "Terenowo-rekreacyjne (SUV) - B MAŁE",
  "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA",
  "Terenowo-rekreacyjne (SUV) - D ŚREDNIA",
  "Terenowo-rekreacyjne (SUV) - E WYŻSZA",
  "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE",
  "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE",
  "Vany - B MICROVANY",
  "Vany - C MINIVANY",
  "Vany - D VANY",
  "Vany - E WYŻSZA",
  "Vany - F LUKSUSOWE",
];

const ALL_ENGINE_TYPES: string[] = [
  "Benzyna (PB)",
  "Benzyna mHEV (PB-mHEV)",
  "Diesel (ON)",
  "Diesel mHEV (ON-mHEV)",
  "Elektryczny (BEV)",
  "Hybryda (HEV)",
  "LPG",
  "Plug-in Hybrid (PHEV)",
  "Wodór (FCEV)",
];
interface VehicleRowCardProps {
  vehicle: FleetVehicleView;
  handleOpenSavedJson: (id: string, titleName: string) => void;
  onRefresh: () => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  crossCardAlerts?: DiscountAlert[];
  globalSettings?: ControlCenterSettings | null;
  isHighlighted?: boolean;
  bodyTypes?: { id: number; name: string; vehicle_class: string }[];
  paintTypes?: { id: number; name: string; [key: string]: unknown }[];

}

export function VehicleRowCard({
  vehicle,
  handleOpenSavedJson,
  onRefresh,
  isSelected = false,
  onToggleSelect,
  crossCardAlerts = [],
  globalSettings,
  isHighlighted = false,
  bodyTypes,
  paintTypes,
}: VehicleRowCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const scrolledToMatrixRef = useRef(false);
  // Subcomponent states
  const [activeKalkulacjaId, setActiveKalkulacjaId] = useState<string | null>(null);
  const [activeKalkulacjaNumer, setActiveKalkulacjaNumer] = useState<string | null>(null);
  const [hasAttemptedAutoLoadHistory, setHasAttemptedAutoLoadHistory] = useState(false);


  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [isBrochureModalOpen, setIsBrochureModalOpen] = useState(false);
  const [brochureData, setBrochureData] = useState<Record<string, unknown> | null>(null);
  const [brochureImages, setBrochureImages] = useState<string[]>([]);
  const [isGeneratingBrochure, setIsGeneratingBrochure] = useState(false);

  const [localMappedData, setLocalMappedData] = useState<MappedData | null>(null);
  const serverMappedData = vehicle.synthesis_data?.mapped_ai_data as MappedData | undefined;
  const mappedData = localMappedData || serverMappedData;

  const [catalogBasePriceNet, setCatalogBasePriceNet] = useState<number>(() => {
    const aiBase = parsePriceToNumber(vehicle.base_price);
    const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
    const val = isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100;
    return isNaN(val) ? 0 : val;
  });

  // Hook 1: Synchronizacja bazy danych / zmiana parametrów (Direct Save / Remap AI)
  const { isSavingFields, handleDirectSave, isRemappingClassification, handleRemapClassification } = useVehicleDataSync(vehicle, onRefresh, setLocalMappedData);

  // Hook: CRUD reference data for manual edit dropdowns (bodyTypes now passed via props)

  // Auto-detect metalic function needs to be passed down
  const autoDetectMetalic = useCallback((): boolean => {
    const cs = (vehicle.synthesis_data as Record<string, Record<string, unknown>>)?.card_summary;
    const color = (vehicle.exterior_color || "").toLowerCase();
    const metallicKeywords = ["metalic", "metalik", "metallic", "metalizow", "perłowy", "pearl", "mica", "xirallic", "special efekt", "dwuwarstwow"];
    if (metallicKeywords.some(kw => color.includes(kw))) return true;
    const nonMetallicKeywords = ["solido", "uni ", "akrylow", "jednowarstwow"];
    if (nonMetallicKeywords.some(kw => color.includes(kw))) return false;
    if (cs?.is_metalic_paint === true) return true;
    if (cs?.is_metalic_paint === false) return false;
    return false;
  }, [vehicle.synthesis_data, vehicle.exterior_color]);

  useEffect(() => {
    if (vehicle.id) {
      // Eagerly preload this vehicle's features into the global cache
      // The hook manages its own internal queue to avoid blasting the API
      queuePreloadVehicleFeatures(vehicle.id);
    }
  }, [vehicle.id]);

  // Hook 2: Parametry Finansowe / Formularz Setupu Kalkulatora
  const {
    wiborPct, setWiborPct,
    marginPct, setMarginPct,
    pricingMarginPct, setPricingMarginPct,
    initialDepositPct, setInitialDepositPct,
    otherServiceCosts, setOtherServiceCosts,
    expressPaysInsurance, setExpressPaysInsurance,
    replacementCar, setReplacementCar,
    gpsRequired, setGpsRequired,
    includeServicing, setIncludeServicing,
    hookInstallation, setHookInstallation,
    tireClass, setTireClass,
    tireCountMode, setTireCountMode,
    tireCostCorrectionEnabled, setTireCostCorrectionEnabled,
    tireCostCorrectionMap, setTireCostCorrectionMap,
    rimDiameter, setRimDiameter,
    serviceCostType, setServiceCostType,
    vehicleVintage, setVehicleVintage,
    paintCategoryId, setPaintCategoryId,
    isSavingSetup, handleSaveSetup
  } = useVehicleFinancing(vehicle, autoDetectMetalic, setCatalogBasePriceNet, globalSettings);

  // Hook 3: Readiness Check API
  // body_type: priorytet: localMappedData → mappedData → card_summary (przez widok: vehicle.body_style)
  const resolvedBodyType = localMappedData?.body_type || mappedData?.body_type || vehicle.body_style || undefined;
  const { readinessResult } = useVehicleReadiness(vehicle, mappedData, paintCategoryId === 2 || paintCategoryId === 3, resolvedBodyType);

  // Extract drive type — priorytet: mapped_ai_data → card_summary (JSONB) → widok SQL
  const DRIVE_TYPE_MAP: Record<string, string> = {
    "Napęd FWD": "4x2 (FWD)", "Napęd RWD": "4x2 (RWD)", "Napęd AWD": "4x4 (AWD)",
    "FWD": "4x2 (FWD)", "RWD": "4x2 (RWD)", "AWD": "4x4 (AWD)",
  };
  const rawDriveTypeFromSynthesis = (vehicle.synthesis_data as Record<string, Record<string, unknown>> | undefined)
    ?.card_summary?.drive_type as string | undefined;
  // Fallback do vehicle.drive_type zmapowanego przez fleet_management_view (z card_summary.drive_type)
  const rawDriveType = rawDriveTypeFromSynthesis || vehicle.drive_type || "";
  const detectedDriveType = rawDriveType
    ? (DRIVE_TYPE_MAP[rawDriveType] ?? rawDriveType)
    : "";
  const driveType = mappedData?.drive_type || detectedDriveType;

  // Hook 4: Param Preview API
  const { paramPreview, controlCenter } = useVehicleParamPreview(
    readinessResult?.samar_class_id || null,
    readinessResult?.fuel_type_id || null,
    vehicle.brand || undefined,
    vehicle.fuel || undefined,
    driveType || undefined,
    vehicle.transmission || undefined,
    serviceCostType,
    60000, // Default target mileage for preview
    tireClass,
    rimDiameter,
    vehicleVintage,
    paintCategoryId === 2 || paintCategoryId === 3
  );

  // Restore saved calculator_setup from synthesis_data on load or update
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setup = (vehicle.synthesis_data as any)?.calculator_setup;
    
    // Always sync auto-detected properties when synthesis_data changes if they are missing in setup
    if (!setup) {
      setPaintCategoryId(autoDetectMetalic() ? 2 : 1);
      const cs = (vehicle.synthesis_data as Record<string, Record<string, unknown>>)?.card_summary;
      setHookInstallation(cs?.has_tow_hook === true);
      setVehicleVintage(cs?.is_current_year_vehicle === false ? "previous" : "current");
      
      const wheels = vehicle.wheels || "";
      const match = wheels.match(/(\d{2})/);
      if (match) setRimDiameter(parseInt(match[1], 10));

      const aiBase = parsePriceToNumber(vehicle.base_price);
      const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
      setCatalogBasePriceNet(isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100);
      return;
    }

    // Financial params
    if (setup.financial_params) {
      const fp = setup.financial_params;
      if (fp.wibor_pct != null) setWiborPct(fp.wibor_pct);
      if (fp.margin_pct != null) setMarginPct(fp.margin_pct);
      if (fp.pricing_margin_pct != null) setPricingMarginPct(fp.pricing_margin_pct);
      if (fp.initial_deposit_pct != null) setInitialDepositPct(fp.initial_deposit_pct);
      if (fp.other_service_costs != null) setOtherServiceCosts(fp.other_service_costs);
      if (fp.other_service_costs != null) setOtherServiceCosts(fp.other_service_costs);
      
      if (fp.catalog_base_price_net != null && fp.catalog_base_price_net > 0) {
        setCatalogBasePriceNet(fp.catalog_base_price_net);
      } else {
        const aiBase = parsePriceToNumber(vehicle.base_price);
        const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
        setCatalogBasePriceNet(isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100);
      }
    } else {
      const aiBase = parsePriceToNumber(vehicle.base_price);
      const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
      setCatalogBasePriceNet(isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100);
    }
    // Toggles
    if (setup.toggles) {
      const t = setup.toggles;
      if (t.express_pays_insurance != null) setExpressPaysInsurance(t.express_pays_insurance);
      if (t.replacement_car != null) setReplacementCar(t.replacement_car);
      if (t.gps_required != null) setGpsRequired(t.gps_required);
      if (t.include_servicing != null) setIncludeServicing(t.include_servicing);
      if (t.hook_installation != null) setHookInstallation(t.hook_installation);
    }
    // Tire params
    if (setup.tire_params) {
      const tp = setup.tire_params;
      if (tp.tire_class != null) setTireClass(tp.tire_class);
      if (tp.tire_count_mode != null) setTireCountMode(tp.tire_count_mode);
      if (tp.tire_cost_correction_enabled != null) setTireCostCorrectionEnabled(tp.tire_cost_correction_enabled);
      if (tp.tire_cost_correction_map != null && typeof tp.tire_cost_correction_map === "object") {
        setTireCostCorrectionMap(tp.tire_cost_correction_map as Record<string, number>);
      } else {
        setTireCostCorrectionMap({});
      }
      if (tp.rim_diameter != null) {
        setRimDiameter(tp.rim_diameter);
      } else {
        const wheels = vehicle.wheels || "";
        const match = wheels.match(/(\d{2})/);
        if (match) setRimDiameter(parseInt(match[1], 10));
      }
    } else {
      const wheels = vehicle.wheels || "";
      const match = wheels.match(/(\d{2})/);
      if (match) setRimDiameter(parseInt(match[1], 10));
    }
    // Other
    if (setup.service_cost_type) setServiceCostType(setup.service_cost_type);
    if (setup.vehicle_vintage) setVehicleVintage(setup.vehicle_vintage);
    // Paint category migration
    if (setup.paint_category_id != null) {
      setPaintCategoryId(setup.paint_category_id);
    } else if (setup.is_metalic != null) {
      const keywordDetected = autoDetectMetalic();
      const color = (vehicle.exterior_color || "").toLowerCase();
      const hasKeyword = ["metalic", "metalik", "metallic", "metalizow", "perłowy", "pearl", "mica", "xirallic", "special efekt", "dwuwarstwow"].some(kw => color.includes(kw))
        || ["solido", "uni ", "akrylow", "jednowarstwow"].some(kw => color.includes(kw));
      const legacyVal = hasKeyword ? keywordDetected : setup.is_metalic;
      setPaintCategoryId(legacyVal ? 2 : 1);
    } else {
      setPaintCategoryId(autoDetectMetalic() ? 2 : 1);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.id, vehicle.synthesis_data, vehicle.exterior_color, vehicle.wheels]);





  const {
    customServiceOptions,
    customFactoryOptions,
    isSavingServices,
    handleUpdateServiceOptionName,
    handleUpdateServiceOptionPrice,
    handleUpdateServiceOptionIncludeInWr,
    handleRemoveServiceOption,
    handleAddManualServiceOption,
    handleUpdateFactoryOptionName,
    handleUpdateFactoryOptionPrice,
    handleUpdateFactoryOptionNoDiscount,
    handleRemoveFactoryOption,
    handleAddManualFactoryOption,
    handleRestoreAllOptions,
    handleSaveAllOptions,
  } = useVehicleOptionsManager(vehicle, onRefresh);

  const {
    isMapping,
    handleSamarCategoryChange,
    handleEngineCategoryChange,
    handleDriveTypeChange,
    handleBodyTypeChange,
    handleConfigurationCodeChange,
    handleVehicleTypeChange,
    handleMapDataSilent,
    handleTransmissionChange,
  } = useVehicleMetaManager(

    vehicle,
    serverMappedData,
    localMappedData,
    setLocalMappedData
  );

  useEffect(() => {
    if (isExpanded && vehicle.synthesis_data && !mappedData && !isMapping) {
      handleMapDataSilent();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded, mappedData, vehicle.synthesis_data]);

  // Auto-load latest calculation history on mount
  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    if (!hasAttemptedAutoLoadHistory && !activeKalkulacjaId && vehicle.id) {
      setHasAttemptedAutoLoadHistory(true);
      const fetchLatestCalc = async () => {
        try {
          const res = await apiClient.fetch(`/api/kalkulacje/vehicle/${vehicle.id}`, {
            signal: controller.signal
          });
          if (res.ok) {
            const data = await res.json();
            if (mounted && data && data.length > 0) {
              const latest = data[0];
              setActiveKalkulacjaId(latest.id);
              setActiveKalkulacjaNumer(latest.numer_kalkulacji);
            }
          }
        } catch (err: unknown) {
          if ((err as Error).name !== 'AbortError') {
            console.error("Silent err auto-loading latest calc:", err);
          }
        }
      };
      // adding a small delay to avoid hammering the connection pool instantly for all rows
      const timeout = setTimeout(fetchLatestCalc, 100);
      
      return () => {
        mounted = false;
        clearTimeout(timeout);
        controller.abort();
      };
    }
  }, [hasAttemptedAutoLoadHistory, activeKalkulacjaId, vehicle.id]);

  // Auto-expand + auto-scroll to matrix when highlighted via deep-link
  useEffect(() => {
    if (!isHighlighted || scrolledToMatrixRef.current) return;
    if (!activeKalkulacjaId) return; // wait for calc ID to load first

    // Expand the card
    if (!isExpanded) setIsExpanded(true);

    // After expansion, poll for the matrix section to appear
    let attempts = 0;
    const tryScrollToMatrix = () => {
      const el = document.getElementById(`vehicle-matrix-${vehicle.id}`);
      if (el) {
        scrolledToMatrixRef.current = true;
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      } else if (attempts < 15) {
        attempts++;
        setTimeout(tryScrollToMatrix, 200);
      }
    };
    // Small delay to let React render the expanded content first
    setTimeout(tryScrollToMatrix, 150);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHighlighted, activeKalkulacjaId]);

  // ── Processing stages for progress stepper ──
  const PROCESSING_STAGES = [
    { key: "uploading", label: "Upload pliku do chmury" },
    { key: "detecting_vehicles", label: "Wykrywanie pojazdów w dokumencie" },
    { key: "extracting_twin", label: "Bliźniak cyfrowy (Docling + Gemini 2.5 Pro)" },
    { key: "generating_summary", label: "Generowanie podsumowania" },
    { key: "matching_discounts", label: "Dopasowywanie rabatów" },
    { key: "mapping_data", label: "Mapowanie danych AI" },
    { key: "enriching_features", label: "Wzbogacanie cech i kalkulacja LTR" },
  ];

  // Match multi-vehicle dynamic statuses like "extracting_twin_2_of_5"
  const rawStatus = vehicle.verification_status || "";
  const isMultiTwinStatus = rawStatus.startsWith("extracting_twin_");
  const normalizedStatus = isMultiTwinStatus ? "extracting_twin" : rawStatus;

  const processingStatuses = new Set([
    "processing", "uploading", "detecting_vehicles", "extracting_twin",
    "generating_summary", "matching_discounts", "mapping_data", "enriching_features",
  ]);

  const {
    discountMode,
    setDiscountMode,
    customDiscountPctRaw,
    setCustomDiscountPctRaw,
    aiExtractedBasePrice,
    calculationBlockReason,
    dynamicTotalOptionsPrice,
    totalCatalogPriceNet,
    discountableOptionsTotal,
    nonDiscountableOptionsTotal,
    customServiceOptionsPriceTotal,
    isDealerOffer,
    offerDiscountPercentage,
    suggestedDiscountPct,
    activeDiscountPct,
    activeFinalPriceNet,
    formatCalculatedPrice,
  } = useVehiclePricingManager({
    vehicle,
    catalogBasePriceNet,
    customFactoryOptions,
    customServiceOptions,
  });



  const isProcessing = processingStatuses.has(normalizedStatus);

  // Cancelled vehicles should not render at all (cancel = delete)
  if (vehicle.verification_status === "cancelled") {
    return null;
  }

  if (vehicle.verification_status?.startsWith("error")) {
    const handleDeleteError = async () => {
      // Dispatch event to let parent (useVehicles via VehicleTable) handle it through the backend API
      window.dispatchEvent(new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } }));
    };

    return (
      <div className={cn(
        "bg-white rounded-xl border shadow-sm p-5 transition-all",
        "border-red-300 ring-4 ring-red-50"
      )}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            <div>
              <h3 className="text-sm font-semibold text-red-800">
                Błąd przetwarzania dokumentu
              </h3>
              <p className="text-xs text-red-600 mt-0.5">
                Nie udało się wyekstrahować bliźniaka cyfrowego.
              </p>
            </div>
          </div>

          <button
            onClick={handleDeleteError}
            className="flex items-center gap-1.5 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 px-3 py-1.5 rounded-lg transition-colors border border-slate-200"
            title="Usuń wpis"
          >
            <X className="w-3.5 h-3.5" />
            Usuń wpis
          </button>
        </div>

        {vehicle.notes && (
          <div className="mt-3 ml-2 p-3 bg-red-50/50 rounded-md border border-red-100">
            <p className="text-xs text-red-800 font-mono whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
              {vehicle.notes}
            </p>
          </div>
        )}
      </div>
    );
  }

  if (isProcessing) {
    const currentStageIndex = PROCESSING_STAGES.findIndex(
      (s) => s.key === normalizedStatus
    );
    // "processing" (legacy) maps to step 0
    const activeIndex = normalizedStatus === "processing" ? 0 : currentStageIndex;

    const handleCancel = async () => {
      // Potwierdzenie usunięcia dokumentu odbywa się natywnie przez modale VehicleTable (jeśli odpalane jest cancel = delete)
      // Ponieważ "Cancel" wymaga wywołania endpointu `/api/cancel-processing`, zrobimy to hybrydowo: 
      // anulowanie usuwa wpis wizualnie z db.
      try {
        const response = await apiClient.fetch(`/api/cancel-processing`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ vehicle_id: vehicle.id }),
        });
        if (!response.ok) throw new Error("Cancel failed");
        // Cancel = delete — remove the vehicle after stopping processing
        window.dispatchEvent(new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } }));
      } catch (err) {
        console.error("Cancel error, attempting direct Supabase cleanup:", err);
        try {
            // Plan B: bezpośrednie skasowanie wiersza przez Supabase JS jeśli backend leży
            // supabase already imported
            // fallback using central supabase client instead of local one
            await supabase.from("vehicle_synthesis").delete().eq("id", vehicle.id);
            window.dispatchEvent(new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } }));
        } catch (dbErr) {
            console.error("Direct Supabase cleanup failed:", dbErr);
            alert("Nie udało się anulować przetwarzania ani skasować zawieszonego wiersza.");
        }
      }
    };

    return (
      <div className={cn(
        "bg-white rounded-xl border shadow-sm p-5 transition-all",
        "border-blue-200"
      )}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
            <div>
              <h3 className="text-sm font-semibold text-slate-800">
                Przetwarzanie dokumentu...
              </h3>
              <p className="text-xs text-slate-500">
                Bliźniak cyfrowy w fazie tworzenia
              </p>
            </div>
          </div>

          <button
            onClick={handleCancel}
            className="flex items-center gap-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors border border-red-100 hover:border-red-200"
            title="Anuluj przetwarzanie"
          >
            <X className="w-3.5 h-3.5" />
            Anuluj
          </button>
        </div>

        {/* Progress stepper */}
        <div className="space-y-1.5 ml-2">
          {PROCESSING_STAGES.map((stage, idx) => {
            let icon: React.ReactNode;
            let textClass: string;

            if (idx < activeIndex) {
              // Completed
              icon = <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center"><svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg></div>;
              textClass = "text-emerald-700 font-medium";
            } else if (idx === activeIndex) {
              // Active
              icon = (
                <div className="w-4 h-4 relative flex items-center justify-center">
                  <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
                </div>
              );
              textClass = "text-blue-700 font-semibold";
            } else {
              // Future
              icon = <div className="w-4 h-4 rounded-full border-2 border-slate-200" />;
              textClass = "text-slate-400";
            }

            return (
              <div key={stage.key} className="flex items-center gap-2.5 py-0.5">
                {icon}
                <span className={cn("text-xs transition-colors", textClass)}>
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Extract SAMAR candidates for reranking dropdown
  const samarCandidates: { klasa: string; confidence: number }[] =
    ((vehicle.synthesis_data?.mapped_ai_data as MappedData & { samar_candidates?: { klasa: string; confidence: number }[] })?.samar_candidates) || [];

  // Extract Engine candidates for reranking dropdown
  const engineCandidates: { klasa: string; confidence: number }[] =
    ((vehicle.synthesis_data?.mapped_ai_data as MappedData & { engine_candidates?: { klasa: string; confidence: number }[] })?.engine_candidates) || [];

  // Map transmission to dictionary values
  const rawTransmission = localMappedData?.transmission || mappedData?.transmission || vehicle.transmission || "";
  const tLower = rawTransmission.toLowerCase();
  const isAuto = tLower.includes("automat") || tLower.includes("dsg") || tLower.includes("s-tronic") || tLower.includes("tiptronic") || tLower.includes("steptronic");
  const isMan = tLower.includes("manual") || tLower.includes("ręczna");
  
  let detectedTransmission = rawTransmission;
  if (isAuto) detectedTransmission = "Automatyczna";
  else if (isMan) detectedTransmission = "Manualna";
  
  const transmission = localMappedData?.transmission || mappedData?.transmission || detectedTransmission;

  // Construct the unified technical description for the header
  const vehicleTypeHint = localMappedData?.vehicle_type || mappedData?.vehicle_type || vehicle.document_category || vehicle.vehicle_class;
  
  const technicalDescriptionParts = [
    vehicle.powertrain,
    vehicleTypeHint,
    driveType,
    transmission,
    resolvedBodyType
  ].filter(part => part && part.trim() !== "" && part !== "Brak" && part !== "-");
  
  const technicalDescription = technicalDescriptionParts.join(" • ");

  return (
    <div
      id={`vehicle-row-${vehicle.id}`}
      data-vehicle-id={vehicle.id}
      className={cn(
        "bg-white rounded-xl border transition-all duration-300 shadow-sm overflow-hidden group hover:shadow-lg",
        isExpanded ? "border-blue-300 ring-4 ring-blue-50/50" : "border-slate-200 hover:border-blue-400",
        isHighlighted && !isExpanded && "ring-4 ring-amber-300 border-amber-400 animate-highlight-fade"
      )}
    >
      <VehicleBaseInfo 
        vehicle={vehicle}
        isExpanded={isExpanded}
        onToggleExpand={() => setIsExpanded(!isExpanded)}
        activeFinalPriceNet={activeFinalPriceNet}
        totalCatalogPriceNet={totalCatalogPriceNet}
        formatCalculatedPrice={formatCalculatedPrice}
        onConfigurationCodeChange={handleConfigurationCodeChange}
        isSelected={isSelected}
        onToggleSelect={onToggleSelect}
        crossCardAlerts={crossCardAlerts}
        discountMode={discountMode}
        setDiscountMode={setDiscountMode}
        customDiscountPctRaw={customDiscountPctRaw}
        setCustomDiscountPctRaw={setCustomDiscountPctRaw}
        offerDiscountPercentage={offerDiscountPercentage}
        suggestedDiscountPct={suggestedDiscountPct}
        technicalDescription={technicalDescription}
      />


      {isExpanded && (
        <div className="border-t border-slate-100 bg-slate-50/50 p-4 sm:p-6 animate-in fade-in slide-in-from-top-2 duration-300 ease-out relative">
          <div className="flex flex-col gap-6 items-start w-full">
            
            {/* Section 2 (moved to top): Summary and Details */}
            <div className="w-full flex flex-col gap-6">

              {/* Conditional rendering for verification status */}
              {vehicle.verification_status === "cancelled" && (
                <div className={cn("p-6 rounded-lg text-sm border", isSelected ? "border-[var(--brand-primary)]" : "border-[var(--system-border)]")}>
                  <div className="flex justify-between items-center text-red-500 mb-2">
                    <span>{vehicle.id}</span>
                    <span>Przerwano przez użytkownika</span>
                  </div>
                </div>
              )}

              {vehicle.verification_status === "moved_to_library" && (
                <div className={cn("p-6 rounded-lg text-sm border", isSelected ? "border-[var(--brand-primary)]" : "border-[var(--system-border)]")}>
                  <div className="flex justify-between items-center text-blue-500 mb-2">
                    <span>{vehicle.id}</span>
                    <span>Przeniesiono do Biblioteki Cenników</span>
                  </div>
                </div>
              )}

              {vehicle.verification_status === "error" && (
                <div className={cn("p-6 rounded-lg text-sm border", isSelected ? "border-[var(--brand-primary)]" : "border-[var(--system-border)]")}>
                  <div className="flex justify-between items-center text-red-500 mb-2">
                    <span>{vehicle.id}</span>
                    <span>Wystąpił błąd podczas przetwarzania</span>
                  </div>
                </div>
              )}



              <div className="space-y-4">
                <VehicleSummaryCard 
                  vehicle={vehicle} 
                  mappedData={mappedData}
                  samarCandidates={samarCandidates}
                  allSamarClasses={ALL_SAMAR_CLASSES}
                  onSamarCategoryChange={handleSamarCategoryChange}
                  engineCandidates={engineCandidates}
                  allEngineTypes={ALL_ENGINE_TYPES}
                  onEngineCategoryChange={handleEngineCategoryChange}
                  driveType={driveType}
                  onDriveTypeChange={handleDriveTypeChange}
                  transmission={transmission}
                  onTransmissionChange={handleTransmissionChange}
                  bodyType={resolvedBodyType}
                  onBodyTypeChange={handleBodyTypeChange}
                  onVehicleTypeChange={handleVehicleTypeChange}
                  bodyTypeOptions={bodyTypes}
                  onDirectSave={handleDirectSave}
                  isSaving={isSavingFields}
                  onRemapClassification={handleRemapClassification}
                  isRemapping={isRemappingClassification}
                />
                <VehicleEquipmentCard
                  vehicle={vehicle}
                  customFactoryOptions={customFactoryOptions}
                  handleUpdateFactoryOptionName={handleUpdateFactoryOptionName}
                  handleUpdateFactoryOptionPrice={handleUpdateFactoryOptionPrice}
                  handleUpdateFactoryOptionNoDiscount={handleUpdateFactoryOptionNoDiscount}
                  handleRemoveFactoryOption={handleRemoveFactoryOption}
                  handleAddManualFactoryOption={handleAddManualFactoryOption}
                  activeDiscountPct={activeDiscountPct}
                />
                <VehicleFeaturesCard
                  vehicleId={vehicle.id}
                  vehicleTypeHint={localMappedData?.vehicle_type || mappedData?.vehicle_type || vehicle.document_category || vehicle.vehicle_class}
                />
              </div>
            </div>

            {/* Section 1 (moved to bottom): Financial Config & Actions */}
            <div className="w-full flex flex-col gap-4">
              <VehicleFinancialOptions 
                 vehicle={vehicle}
                 totalCatalogPriceNet={totalCatalogPriceNet}
                 activeFinalPriceNet={activeFinalPriceNet}
                 dynamicTotalOptionsPrice={dynamicTotalOptionsPrice}
                 catalogBasePriceNet={catalogBasePriceNet}
                 setCatalogBasePriceNet={setCatalogBasePriceNet}
                 aiExtractedBasePrice={aiExtractedBasePrice}
                 discountableOptionsTotal={discountableOptionsTotal}
                 nonDiscountableOptionsTotal={nonDiscountableOptionsTotal}
                 serviceOptionsTotal={customServiceOptionsPriceTotal}
                 isDealerOffer={isDealerOffer}
                 offerDiscountPercentage={offerDiscountPercentage}
                 suggestedDiscountPct={suggestedDiscountPct}
                 activeDiscountPct={activeDiscountPct}
                 customServiceOptions={customServiceOptions}
                 handleUpdateServiceOptionName={handleUpdateServiceOptionName}
                 handleUpdateServiceOptionPrice={handleUpdateServiceOptionPrice}
                 handleUpdateServiceOptionIncludeInWr={handleUpdateServiceOptionIncludeInWr}
                 handleRemoveServiceOption={handleRemoveServiceOption}
                 handleAddManualServiceOption={handleAddManualServiceOption}
                 handleRestoreAllOptions={handleRestoreAllOptions}
                 handleSaveAllOptions={handleSaveAllOptions}
                 isSavingServices={isSavingServices}
                 // Financial parameters
                 wiborPct={wiborPct || 0}
                 setWiborPct={setWiborPct}
                 marginPct={marginPct || 0}
                 setMarginPct={setMarginPct}
                 pricingMarginPct={pricingMarginPct || 0}
                 setPricingMarginPct={setPricingMarginPct}
                 initialDepositPct={initialDepositPct || 0}
                 setInitialDepositPct={setInitialDepositPct}
                 otherServiceCosts={otherServiceCosts}
                 setOtherServiceCosts={setOtherServiceCosts}
                 // Toggles
                 expressPaysInsurance={expressPaysInsurance}
                 setExpressPaysInsurance={setExpressPaysInsurance}
                 replacementCar={replacementCar}
                 setReplacementCar={setReplacementCar}
                 gpsRequired={gpsRequired}
                 setGpsRequired={setGpsRequired}
                 includeServicing={includeServicing}
                 setIncludeServicing={setIncludeServicing}
                 hookInstallation={hookInstallation}
                 setHookInstallation={setHookInstallation}
                 // Tire parameters
                 tireClass={tireClass}
                 setTireClass={setTireClass}
                 tireCountMode={tireCountMode}
                 setTireCountMode={setTireCountMode}
                 tireCostCorrectionEnabled={tireCostCorrectionEnabled}
                 setTireCostCorrectionEnabled={setTireCostCorrectionEnabled}
                 tireCostCorrectionMap={tireCostCorrectionMap}
                 setTireCostCorrectionMap={setTireCostCorrectionMap}
                 rimDiameter={rimDiameter}
                 setRimDiameter={setRimDiameter}
                 // Service cost type
                 serviceCostType={serviceCostType}
                 setServiceCostType={setServiceCostType}
                 // Vehicle vintage & metalic
                 vehicleVintage={vehicleVintage}
                 setVehicleVintage={setVehicleVintage}
                 paintCategoryId={paintCategoryId}
                 setPaintCategoryId={setPaintCategoryId}
                 paintTypes={paintTypes}
                 isMetalicAutoDetected={autoDetectMetalic()}
                 hookAutoDetected={((vehicle.synthesis_data as Record<string, Record<string, unknown>>)?.card_summary)?.has_tow_hook === true}
                 vintageAutoDetected={((vehicle.synthesis_data as Record<string, Record<string, unknown>>)?.card_summary)?.is_current_year_vehicle != null}
                 // Price context for czynsz inicjalny calculations
                 activeFinalPriceForDeposit={activeFinalPriceNet}
                 crossCardAlerts={crossCardAlerts}
                 paramPreview={paramPreview}
                 controlCenter={controlCenter}
              />
              <div className="flex flex-col gap-3 pt-4 border-t border-slate-200 bg-slate-50/50 rounded-b-xl">
                 <VehicleActionButtons
                   vehicle={vehicle}
                   isSavingSetup={isSavingSetup}
                   handleSaveSetup={() => handleSaveSetup(activeDiscountPct, activeFinalPriceNet, catalogBasePriceNet)}
                   pricingMarginPct={pricingMarginPct || 0}
                   initialDepositPct={initialDepositPct || 0}
                   expressPaysInsurance={expressPaysInsurance}
                   replacementCar={replacementCar}
                   gpsRequired={gpsRequired}
                   includeServicing={includeServicing}
                   hookInstallation={hookInstallation}
                   tireClass={tireClass}
                   tireCountMode={tireCountMode}
                   tireCostCorrectionEnabled={tireCostCorrectionEnabled}
                   tireCostCorrectionMap={tireCostCorrectionMap}
                   rimDiameter={rimDiameter}
                   serviceCostType={serviceCostType}
                   vehicleVintage={vehicleVintage}
                   paintCategoryId={paintCategoryId}
                   activeDiscountPct={activeDiscountPct}
                   activeFinalPrice={activeFinalPriceNet}
                   brochureData={brochureData}
                   setIsBrochureModalOpen={setIsBrochureModalOpen}
                   isGeneratingBrochure={isGeneratingBrochure}
                   setIsGeneratingBrochure={setIsGeneratingBrochure}
                   setBrochureData={setBrochureData}
                   setBrochureImages={setBrochureImages}
                   handleOpenSavedJson={handleOpenSavedJson}
                   isViewerOpen={isViewerOpen}
                   setIsViewerOpen={setIsViewerOpen}
                   calculationBlockReason={calculationBlockReason}
                   onCalculationCreated={(id, numer) => {
                     setActiveKalkulacjaId(id);
                     setActiveKalkulacjaNumer(numer);
                     if (!isExpanded) setIsExpanded(true);
                   }}
                   activeKalkulacjaId={activeKalkulacjaId}
                   activeKalkulacjaNumer={activeKalkulacjaNumer}
                 />
              </div>

              {/* PDF Viewer — pełna szerokość, pod przyciskami akcji */}
              {isViewerOpen && vehicle.raw_pdf_url && (
                <div className="w-full border border-slate-200 rounded-lg shadow-sm overflow-auto">
                  <PDFViewerFrame url={vehicle.raw_pdf_url} />
                </div>
              )}
            </div>

            {activeKalkulacjaId && activeKalkulacjaNumer && (
              <div id={`vehicle-matrix-${vehicle.id}`} className="w-full flex flex-col gap-6">
                <VehicleRowCalculations
                  kalkulacjaId={activeKalkulacjaId}
                  kalkulacjaNumer={activeKalkulacjaNumer}
                  vehicleId={vehicle.id}
                  vehicleName={`${vehicle.brand || "?"} ${vehicle.model}`}
                  powertrain={mappedData?.fuel ? `${mappedData.fuel} ${mappedData.engine_class || ""}`.trim() : (vehicle.powertrain || "")}
                  offerNumber={vehicle.offer_number || ""}
                  configCode={vehicle.configuration_code || ""}
                  basePrice={catalogBasePriceNet}
                />
              </div>
            )}
          </div>
        </div>
      )}
      {isBrochureModalOpen && brochureData && (
         <BrochureBuilderModal 
            vehicle={vehicle}
            initialBrochureData={brochureData}
            initialImages={brochureImages}
            onClose={() => setIsBrochureModalOpen(false)} 
         />
      )}
    </div>
  );
}



