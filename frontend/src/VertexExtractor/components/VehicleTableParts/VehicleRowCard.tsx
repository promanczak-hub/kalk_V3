import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Loader2, X, AlertTriangle } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView, ModificationEffect, HomologationResponse } from "../../types";
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
import { apiFetch } from "../../../lib/api";
import type { ControlCenterSettings } from "../../../hooks/useCalculator";

// Custom Hooks
import { useVehicleFinancing } from "../../hooks/useVehicleFinancing";
import { useVehicleDataSync } from "../../hooks/useVehicleDataSync";
import { useVehicleReadiness } from "../../hooks/useVehicleReadiness";
import { useVehicleParamPreview } from "../../hooks/useVehicleParamPreview";
import { useReferenceData } from "../../hooks/useReferenceData";
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
}: VehicleRowCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const scrolledToMatrixRef = useRef(false);
  // Subcomponent states
  const [activeKalkulacjaId, setActiveKalkulacjaId] = useState<string | null>(null);
  const [activeKalkulacjaNumer, setActiveKalkulacjaNumer] = useState<string | null>(null);
  const [hasAttemptedAutoLoadHistory, setHasAttemptedAutoLoadHistory] = useState(false);


  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [isBrochureModalOpen, setIsBrochureModalOpen] = useState(false);
  const [brochureData, setBrochureData] = useState<any | null>(null);
  const [brochureImages, setBrochureImages] = useState<string[]>([]);
  const [isGeneratingBrochure, setIsGeneratingBrochure] = useState(false);

  const [localMappedData, setLocalMappedData] = useState<MappedData | null>(null);
  const serverMappedData = vehicle.synthesis_data?.mapped_ai_data as MappedData | undefined;
  const mappedData = localMappedData || serverMappedData;

  const [catalogBasePriceNet, setCatalogBasePriceNet] = useState<number>(() => {
    const aiBase = parsePriceToNumber(vehicle.base_price);
    const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
    return isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100;
  });

  // Hook 1: Synchronizacja bazy danych / zmiana parametrów (Direct Save / Remap AI)
  const { isSavingFields, handleDirectSave, isRemappingClassification, handleRemapClassification } = useVehicleDataSync(vehicle, onRefresh, setLocalMappedData);

  // Hook: CRUD reference data for manual edit dropdowns
  const { bodyTypes } = useReferenceData();

  // Auto-detect metalic function needs to be passed down
  const autoDetectMetalic = useCallback((): boolean => {
    const cs = (vehicle.synthesis_data as any)?.card_summary;
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
    tireCostCorrection, setTireCostCorrection,
    rimDiameter, setRimDiameter,
    serviceCostType, setServiceCostType,
    vehicleVintage, setVehicleVintage,
    isMetalic, setIsMetalic,
    isSavingSetup, handleSaveSetup
  } = useVehicleFinancing(vehicle, autoDetectMetalic, setCatalogBasePriceNet, globalSettings);

  // Hook 3: Readiness Check API
  const { readinessResult } = useVehicleReadiness(vehicle, mappedData, isMetalic);

  // Hook 4: Param Preview API
  const { paramPreview, controlCenter } = useVehicleParamPreview(
    readinessResult?.samar_class_id,
    readinessResult?.fuel_type_id,
    serviceCostType,
    tireClass,
    rimDiameter,
    vehicleVintage,
    isMetalic
  );

  // Restore saved calculator_setup from synthesis_data on load or update
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setup = (vehicle.synthesis_data as any)?.calculator_setup;
    
    // Always sync auto-detected properties when synthesis_data changes if they are missing in setup
    if (!setup) {
      setIsMetalic(autoDetectMetalic());
      const cs = (vehicle.synthesis_data as any)?.card_summary;
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
      if (tp.tire_cost_correction != null) setTireCostCorrection(tp.tire_cost_correction);
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
    // Metalic: keyword detection always wins over saved value (keywords are deterministic)
    if (setup.is_metalic != null) {
      const keywordDetected = autoDetectMetalic();
      const color = (vehicle.exterior_color || "").toLowerCase();
      const hasKeyword = ["metalic", "metalik", "metallic", "metalizow", "perłowy", "pearl", "mica", "xirallic", "special efekt", "dwuwarstwow"].some(kw => color.includes(kw))
        || ["solido", "uni ", "akrylow", "jednowarstwow"].some(kw => color.includes(kw));
      // If keywords found → trust keyword detection; otherwise use saved value
      setIsMetalic(hasKeyword ? keywordDetected : setup.is_metalic);
    } else {
      setIsMetalic(autoDetectMetalic());
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.id, vehicle.synthesis_data, vehicle.exterior_color, vehicle.wheels]);





  // Determine price domain from deterministic backend detection
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const priceDomain: string = ((vehicle.synthesis_data as any)?.card_summary?._price_domain) || "unknown";

  /** Convert a parsed price to netto, respecting the option's price_type or global domain. */
  const toNettoAware = (rawPrice: number, priceStr?: string, optPriceType?: string): number => {
    if (rawPrice === 0) return 0;
    // Priority: option-level price_type > detected string label > global domain
    const type = optPriceType && optPriceType !== "unknown"
      ? optPriceType
      : priceStr?.toLowerCase().includes("brutto")
        ? "brutto"
        : priceStr?.toLowerCase().includes("netto")
          ? "netto"
          : priceDomain;
    return type === "brutto" ? Math.round((rawPrice / 1.23) * 100) / 100 : rawPrice;
  };

  // Local state for CRUD operations on Service Options
  const initialServiceOptions = useMemo(() => {
    return vehicle.paid_options?.filter(
      (o) => o.category && !o.category.includes("Fabryczna")
    ).map(o => ({
       id: crypto.randomUUID(),
       name: o.name,
       price_net: o.price ? toNettoAware(parsePriceToNumber(o.price), o.price, (o as any).price_type) : 0,
       category: o.category || "Opcja Serwisowa",
       // @ts-expect-error - compatibility with older data model
       include_in_wr: o.include_in_wr || false
    })) || [];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.paid_options, priceDomain]);

  const initialFactoryOptions = useMemo(() => {
    const opts = vehicle.paid_options?.filter(
      (o) => o.category?.includes("Fabryczna") || !o.category
    ).map(o => ({
       id: crypto.randomUUID(),
       name: o.name,
       price_net: o.price ? toNettoAware(parsePriceToNumber(o.price), o.price, (o as any).price_type) : 0,
       category: o.category || "Fabryczna",
       no_discount: (o as any).no_discount === true
    })) || [];

    if (vehicle.exterior_color && vehicle.exterior_color !== "Brak") {
      const isAlreadyAdded = opts.some(
        (opt) =>
          opt.name.toLowerCase().includes("lakier") ||
          vehicle.exterior_color!.toLowerCase().includes(opt.name.toLowerCase())
      );
      if (!isAlreadyAdded) {
        let name = `Lakier: ${vehicle.exterior_color}`;
        let priceNet = 0;
        const match =
          vehicle.exterior_color.match(
            /\((?:dopłata\s*)?([\d\s,.]+\s*(?:PLN|zł|pln|ZŁ).*?)\)/i,
          ) ||
          vehicle.exterior_color.match(/-\s*([\d\s,.]+\s*(?:PLN|zł|pln|ZŁ).*?)/i) ||
          vehicle.exterior_color.match(/(\d[\d\s]*\s*(?:PLN|zł|pln|ZŁ))/i);

        if (match) {
          const priceStr = match[1] || match[0];
          priceNet = toNettoAware(parsePriceToNumber(priceStr), priceStr);
          name = `Lakier: ${vehicle.exterior_color
            .replace(match[0], "")
            .replace(/\(\s*\)/, "")
            .trim()}`;
        }
        opts.unshift({ id: crypto.randomUUID(), name, price_net: priceNet, category: "Fabryczna", no_discount: false });
      }
    }
    return opts;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.paid_options, vehicle.exterior_color, priceDomain]);

   const [customServiceOptions, setCustomServiceOptions] = useState<{id: string, name: string, price_net: number, category: string, effects?: ModificationEffect, include_in_wr?: boolean}[]>([]);
   const [customFactoryOptions, setCustomFactoryOptions] = useState<{id: string, name: string, price_net: number, category: string, no_discount: boolean, effects?: ModificationEffect}[]>([]);
  
  // Set initial state only once or when vehicle completely changes
  useEffect(() => {
     setCustomServiceOptions(initialServiceOptions);
     setCustomFactoryOptions(initialFactoryOptions);
  }, [initialServiceOptions, initialFactoryOptions]);

  const handleUpdateServiceOptionName = (id: string, newName: string) => {
    setCustomServiceOptions(prev => prev.map(opt => opt.id === id ? { ...opt, name: newName } : opt));
  };

  const handleUpdateServiceOptionPrice = (id: string, newPrice: number) => {
    setCustomServiceOptions(prev => prev.map(opt => opt.id === id ? { ...opt, price_net: newPrice } : opt));
  };

  const handleUpdateServiceOptionIncludeInWr = (id: string, include: boolean) => {
    setCustomServiceOptions(prev => prev.map(opt => opt.id === id ? { ...opt, include_in_wr: include } : opt));
  };

  const handleRemoveServiceOption = (id: string) => {
     setCustomServiceOptions(prev => prev.filter(opt => opt.id !== id));
  };

  const handleAddManualServiceOption = () => {
     setCustomServiceOptions(prev => [
       ...prev, 
       { id: crypto.randomUUID(), name: "Nowa Usługa", price_net: 0, category: "Opcja Serwisowa", include_in_wr: false }
     ]);
  };

  const handleUpdateFactoryOptionName = (id: string, newName: string) => {
    setCustomFactoryOptions(prev => prev.map(opt => opt.id === id ? { ...opt, name: newName } : opt));
  };

  const handleUpdateFactoryOptionPrice = (id: string, newPrice: number) => {
    setCustomFactoryOptions(prev => prev.map(opt => opt.id === id ? { ...opt, price_net: newPrice } : opt));
  };

  const handleRemoveFactoryOption = (id: string) => {
     setCustomFactoryOptions(prev => prev.filter(opt => opt.id !== id));
  };

  const handleUpdateFactoryOptionNoDiscount = (id: string, noDiscount: boolean) => {
     setCustomFactoryOptions(prev => prev.map(opt => opt.id === id ? { ...opt, no_discount: noDiscount } : opt));
  };

  const handleAddManualFactoryOption = () => {
     setCustomFactoryOptions(prev => [
       ...prev, 
       { id: crypto.randomUUID(), name: "Nowa Opcja Fabryczna", price_net: 0, category: "Fabryczna", no_discount: false }
     ]);
  };

  const handleRestoreAllOptions = () => {
    if (window.confirm("Czy na pewno chcesz przywrócić oryginalne usługi serwisowe i opcje fabryczne wyekstrahowane z dokumentu bazy? Bieżące niezapisane modyfikacje zostaną utracone.")) {
      setCustomServiceOptions(initialServiceOptions);
       setCustomFactoryOptions(initialFactoryOptions);
    }
  };

  // Store full homologation response temporarily
  const [, setHomologationResult] = useState<HomologationResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    const verifyHomologation = async () => {
      try {
        const mappedData = vehicle.synthesis_data?.mapped_ai_data as MappedData | undefined;
        // Default base payload if missing (for now using 1000kg as fallback or extracting from real schema later)
        const basePayload = (vehicle.synthesis_data as any)?.card_summary?.technical_details?.payload_capacity_kg || 1500;
        
        const payload = {
          vehicle_id: vehicle.id,
          base_samar_category: mappedData?.samar_category,
          base_vehicle_type: mappedData?.vehicle_type,
          base_payload_kg: basePayload,
          service_options: customServiceOptions.map(opt => ({
             name: opt.name,
             category: opt.category,
             price_net: opt.price_net,
             effects: opt.effects
          }))
        };

        const res = await apiFetch(`/api/homologation/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        if (!res.ok) return;
        const data = await res.json();
        if (mounted) {
          console.log("HOMO Response raw:", Array.isArray(data) ? data[0] : data);
          setHomologationResult(Array.isArray(data) ? data[0] : data);
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          // silently fail verification
        }
      }
    };

    const timeout = setTimeout(verifyHomologation, 600);
    return () => {
      mounted = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [customServiceOptions, vehicle.id, vehicle.synthesis_data]);

  const [isSavingServices, setIsSavingServices] = useState(false);


  const handleSaveAllOptions = async () => {
    setIsSavingServices(true);
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      
      if (!updatedJson.card_summary) updatedJson.card_summary = {};
      
      updatedJson.card_summary.paid_options = [
        ...customFactoryOptions.map(opt => ({
           name: opt.name,
           category: opt.category,
           price: String(opt.price_net) + " PLN netto",
           price_net: opt.price_net,
           no_discount: opt.no_discount
        })),
        ...customServiceOptions.map(opt => ({
           name: opt.name,
           category: opt.category,
           price: String(opt.price_net) + " PLN netto",
           price_net: opt.price_net,
           include_in_wr: opt.include_in_wr || false
        }))
      ];

      // Temporary native API call for update instead of hook to avoid refactoring whole component scope for this simple update right now
      // This will be properly separated in a future refactor step
      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;
      
      // Optymalizacja UX: Po zapisaniu opcji, automatycznie wyzwalamy weryfikację cech w tle,
      // żeby sekcja "Cechy Użytkowe" nadążyła za ewentualnymi zmianami w opcjach (np. polem Hak Holowniczy)
      try {
        apiFetch(`/api/features/vehicle/${vehicle.id}/enrich-background`, { method: "POST" })
          .catch(e => console.error("Silent err on bg-enrich:", e));
      } catch {
        // silently ignore error
      }

      onRefresh();
    } catch (err) {
      console.error("Error saving options", err);
      // alert("Błąd podczas zapisu opcji");
    } finally {
      setIsSavingServices(false);
    }
  };

  const [isMapping, setIsMapping] = useState(false);



  // Extract SAMAR candidates for reranking dropdown
  const samarCandidates: { klasa: string; confidence: number }[] =
    ((vehicle.synthesis_data?.mapped_ai_data as MappedData & { samar_candidates?: { klasa: string; confidence: number }[] })?.samar_candidates) || [];

  // Extract Engine candidates for reranking dropdown
  const engineCandidates: { klasa: string; confidence: number }[] =
    ((vehicle.synthesis_data?.mapped_ai_data as MappedData & { engine_candidates?: { klasa: string; confidence: number }[] })?.engine_candidates) || [];



  // Extract drive type from card_summary
  const DRIVE_TYPE_MAP: Record<string, string> = {
    "Napęd FWD": "4x2 (FWD)", "Napęd RWD": "4x2 (RWD)", "Napęd AWD": "4x4 (AWD)",
    "FWD": "4x2 (FWD)", "RWD": "4x2 (RWD)", "AWD": "4x4 (AWD)",
  };
  const rawDriveType = (vehicle.synthesis_data as Record<string, Record<string, unknown>> | undefined)
    ?.card_summary?.drive_type as string | undefined;
  const detectedDriveType = rawDriveType
    ? (DRIVE_TYPE_MAP[rawDriveType] ?? rawDriveType)
    : "";
  const driveType = mappedData?.drive_type || detectedDriveType;

  const handleSamarCategoryChange = async (newCategory: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.samar_category = newCategory;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      // Update local state so UI reflects immediately
      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        samar_category: newCategory,
      }));
    } catch (err) {
      console.error("Error updating SAMAR category", err);
      alert("Błąd zapisu kategorii SAMAR: " + (err instanceof Error ? err.message : "Nieznany b\u0142\u0105d"));
    }
  };

  const handleEngineCategoryChange = async (newCategory: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.fuel = newCategory;

      // Optimistically fetch category for immediate UI update
      const enginesResp = await supabase.from('engines').select('category').eq('name', newCategory);
      const newCategoryClass = enginesResp.data?.[0]?.category;
      if (newCategoryClass) {
         updatedJson.mapped_ai_data.engine_class = newCategoryClass;
      }

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      // Update local state so UI reflects immediately
      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        fuel: newCategory,
        engine_class: newCategoryClass || prev?.engine_class || serverMappedData?.engine_class,
      }));
    } catch (err) {
      console.error("Error updating Engine category", err);
      alert("Błąd zapisu kategorii Silnika: " + (err instanceof Error ? err.message : "Nieznany b\u0142\u0105d"));
    }
  };

  const handleDriveTypeChange = async (newDriveType: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.drive_type = newDriveType;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        drive_type: newDriveType,
      }));
    } catch (err) {
      console.error("Error updating drive type", err);
      alert("Błąd zapisu napędu: " + (err instanceof Error ? err.message : "Nieznany b\u0142\u0105d"));
    }
  };

  const handleBodyTypeChange = async (newBodyType: string) => {
    const rawCandidate = (newBodyType || "").trim();
    if (!rawCandidate) return;

    try {
      let canonicalBodyType = rawCandidate;

      const matchResp = await apiFetch(`/api/match-body-type?body_style_raw=${encodeURIComponent(rawCandidate)}`);
      if (matchResp.ok) {
        const match = await matchResp.json();
        if (match?.matched_name) {
          canonicalBodyType = match.matched_name;
        } else {
          console.warn("Body type not found in dictionary, keeping manual value:", rawCandidate);
        }
      }

      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.body_type = canonicalBodyType;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        body_type: canonicalBodyType,
      }));
    } catch (err) {
      console.error("Error updating body type", err);
      alert("Błąd zapisu nadwozia: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleMapDataSilent = async () => {
    if (!vehicle.synthesis_data) return;
    setIsMapping(true);
    try {
      const response = await apiFetch(`/api/extract/map-vehicle-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_json: vehicle.synthesis_data,
        }),
      });

      if (!response.ok) {
        throw new Error("Błąd podczas wywołania API mapowania danych.");
      }

      const data = await response.json();
      setLocalMappedData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsMapping(false);
    }
  };

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
          const res = await apiFetch(`/api/kalkulacje/vehicle/${vehicle.id}`, {
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
        } catch (err: any) {
          if (err.name !== 'AbortError') {
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

  const [discountMode, setDiscountMode] = useState<"offer" | "suggested" | "custom">(() => {
    const cs = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
    const offerPct = Number(cs?.offer_discount_pct ?? 0);
    const suggestedPct = Number(vehicle.suggested_discount_pct ?? 0);

    if (Number.isFinite(offerPct) && offerPct > 0) return "offer";
    if (Number.isFinite(suggestedPct) && suggestedPct > 0) return "suggested";
    return "offer";
  });
  const [customDiscountPctRaw, setCustomDiscountPctRaw] = useState<string | number>("");

  const customDiscountPct = Number(customDiscountPctRaw) || 0;



  // AI-extracted raw string for comparison display
  const aiExtractedBasePrice = vehicle.base_price || null;
  const AI_PRICE_ALERT_THRESHOLD_PLN = 10;
  const aiBasePriceRaw = parsePriceToNumber(aiExtractedBasePrice || "0");
  const aiBasePriceNet = aiExtractedBasePrice?.toLowerCase().includes("netto")
    ? aiBasePriceRaw
    : Math.round((aiBasePriceRaw / 1.23) * 100) / 100;
  const aiBasePriceDeltaPln = Math.abs(catalogBasePriceNet - aiBasePriceNet);
  const requireManualPriceReview = Boolean(
    aiExtractedBasePrice && aiBasePriceNet > 0 && aiBasePriceDeltaPln > AI_PRICE_ALERT_THRESHOLD_PLN
  );
  const calculationBlockReason = requireManualPriceReview
    ? `Różnica ceny bazowej względem AI wynosi ${aiBasePriceDeltaPln.toFixed(2)} PLN (limit ${AI_PRICE_ALERT_THRESHOLD_PLN} PLN). Zweryfikuj ręcznie i skoryguj cenę.`
    : null;

  // ── Dynamic option splits (must come BEFORE totalCatalogPriceNet) ──
  // These are the source of truth for option prices, not raw vehicle.options_price.
  const factoryOptionsPriceTotal = customFactoryOptions.reduce((acc, curr) => acc + curr.price_net, 0);
  const customServiceOptionsPriceTotal = customServiceOptions.reduce((acc, curr) => acc + curr.price_net, 0);

  const dynamicTotalOptionsPrice = factoryOptionsPriceTotal + customServiceOptionsPriceTotal;

  // Split factory options into discountable / non-discountable (always Netto)
  const discountableOptionsTotal = customFactoryOptions
    .filter(opt => !opt.no_discount)
    .reduce((acc, curr) => acc + curr.price_net, 0);
  const nonDiscountableOptionsTotal = customFactoryOptions
    .filter(opt => opt.no_discount)
    .reduce((acc, curr) => acc + curr.price_net, 0);

  // totalCatalogPriceNet = base + ALL factory options (netto, from managed options — NOT raw vehicle.options_price)
  const totalCatalogPriceNet = catalogBasePriceNet + factoryOptionsPriceTotal;

  const offerFinalPriceRaw = parsePriceToNumber(vehicle.final_price_pln);
  // Detect source price domain (netto vs brutto) ONLY for offer check
  const isSourceNetto = vehicle.base_price?.toLowerCase().includes("netto") ?? false;
  const offerFinalPriceNet = isSourceNetto ? offerFinalPriceRaw : offerFinalPriceRaw / 1.23;

  const hasOfferFinalPrice = Boolean(
    vehicle.final_price_pln &&
    vehicle.final_price_pln !== "Brak" &&
    vehicle.final_price_pln !== vehicle.base_price
  );
  
  // To avoid false positives on dealer offer detection, check if offer is less than total catalog netto
  const isDealerOffer = Boolean(
    hasOfferFinalPrice && offerFinalPriceNet > 0 && offerFinalPriceNet < totalCatalogPriceNet - 1.0
  );
  
  const cardSummary = vehicle.synthesis_data?.card_summary as Record<string, unknown> | undefined;
  const parsedOfferDiscountPct = cardSummary?.offer_discount_pct;

  const hasValidOfferDiscount = Boolean(parsedOfferDiscountPct && Number(parsedOfferDiscountPct) > 0);
  
  // Extend isDealerOffer to include cases where we have an explicitly provided discount percentage
  const isDealerOfferExtended = isDealerOffer || hasValidOfferDiscount;

  const offerDiscountPercentage = parsedOfferDiscountPct
    ? Number(parsedOfferDiscountPct)
    : isDealerOffer && totalCatalogPriceNet > 0
      ? Number((((totalCatalogPriceNet - offerFinalPriceNet) / totalCatalogPriceNet) * 100).toFixed(1))
      : 0;

  const suggestedDiscountPct = vehicle.suggested_discount_pct || 0;
  const suggestedDiscountConfidence = vehicle.suggested_discount_confidence || 0;

  // discountableBaseNet = base + discountable factory options
  const discountableBaseNet = catalogBasePriceNet + discountableOptionsTotal;

  let activeDiscountPct = 0;
  // Default final price: base + all factory options + service options (no discount)
  let activeFinalPriceNet = totalCatalogPriceNet + customServiceOptionsPriceTotal;

  if (discountMode === "offer" && isDealerOfferExtended) {
    activeDiscountPct = offerDiscountPercentage;
    if (parsedOfferDiscountPct && !hasOfferFinalPrice) {
      activeFinalPriceNet = 
        discountableBaseNet * (1 - offerDiscountPercentage / 100)
        + nonDiscountableOptionsTotal
        + customServiceOptionsPriceTotal;
    } else {
      activeFinalPriceNet = offerFinalPriceNet;
    }
  } else if (discountMode === "suggested") {
    activeDiscountPct = suggestedDiscountPct;
    // Discount only the discountable portion (base + discountable opts)
    activeFinalPriceNet =
      discountableBaseNet * (1 - suggestedDiscountPct / 100)
      + nonDiscountableOptionsTotal
      + customServiceOptionsPriceTotal;
  } else if (discountMode === "custom") {
    activeDiscountPct = customDiscountPct;
    activeFinalPriceNet =
      discountableBaseNet * (1 - customDiscountPct / 100)
      + nonDiscountableOptionsTotal
      + customServiceOptionsPriceTotal;
  }

  const formatCalculatedPrice = (val: number) => {
      if (val === 0) return "Brak";
      return `${val.toFixed(2)} PLN netto`;
  };



  const isProcessing = processingStatuses.has(normalizedStatus);

  // Cancelled vehicles should not render at all (cancel = delete)
  if (vehicle.verification_status === "cancelled") {
    return null;
  }

  if (vehicle.verification_status?.startsWith("error")) {
    const handleDeleteError = async () => {
      if (!window.confirm("Czy na pewno chcesz usunąć ten wpis z błędem?")) return;
      try {
        await supabase.from("vehicle_synthesis").delete().eq("id", vehicle.id);
        window.dispatchEvent(new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } }));
      } catch (err) {
        console.error("Direct Supabase cleanup failed:", err);
        alert("Nie udało się skasować wiersza.");
      }
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
      if (!window.confirm("Czy na pewno chcesz anulować przetwarzanie tego dokumentu?")) return;
      try {
        const response = await apiFetch(`/api/cancel-processing`, {
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

  return (
    <div
      id={`vehicle-row-${vehicle.id}`}
      data-vehicle-id={vehicle.id}
      className={cn(
        "bg-white rounded-xl border transition-all duration-200 shadow-sm overflow-hidden group hover:shadow-md",
        isExpanded ? "border-blue-300 ring-4 ring-blue-50/50" : "border-slate-200 hover:border-blue-200",
        isHighlighted && !isExpanded && "ring-4 ring-amber-300 border-amber-400 animate-highlight-fade"
      )}
    >
      <VehicleBaseInfo 
        vehicle={vehicle}
        mappedData={mappedData}
        isExpanded={isExpanded}
        onToggleExpand={() => setIsExpanded(!isExpanded)}
        activeFinalPriceNet={activeFinalPriceNet}
        totalCatalogPriceNet={totalCatalogPriceNet}
        formatCalculatedPrice={formatCalculatedPrice}
        samarCandidates={samarCandidates}
        onSamarCategoryChange={handleSamarCategoryChange}
        allSamarClasses={ALL_SAMAR_CLASSES}
        engineCandidates={engineCandidates}
        onEngineCategoryChange={handleEngineCategoryChange}
        allEngineTypes={ALL_ENGINE_TYPES}
        driveType={driveType}
        onDriveTypeChange={handleDriveTypeChange}
        bodyType={localMappedData?.body_type || mappedData?.body_type || vehicle.body_style || undefined}
        onBodyTypeChange={handleBodyTypeChange}
        bodyTypeOptions={bodyTypes}
        isSelected={isSelected}
        onToggleSelect={onToggleSelect}
        crossCardAlerts={crossCardAlerts}
        readinessResult={readinessResult}
      />

      {isExpanded && (
        <div className="border-t border-slate-100 bg-slate-50/50 p-4 sm:p-6 animate-in fade-in slide-in-from-top-2 duration-300 ease-out">
          {/* Business-style data visualizations */}
          <div className="space-y-4 mb-6">
            <VehicleSummaryCard 
              vehicle={vehicle} 
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

          <VehicleFinancialOptions 
             vehicle={vehicle}
             totalCatalogPriceNet={totalCatalogPriceNet}
             activeFinalPriceNet={activeFinalPriceNet}
             dynamicTotalOptionsPrice={dynamicTotalOptionsPrice}
             catalogBasePriceNet={catalogBasePriceNet}
             setCatalogBasePriceNet={setCatalogBasePriceNet}
             aiExtractedBasePrice={aiExtractedBasePrice}
             aiPriceAlertThresholdPln={AI_PRICE_ALERT_THRESHOLD_PLN}
             requireManualPriceReview={requireManualPriceReview}
             priceDeltaFromAiPln={aiBasePriceDeltaPln}
             discountableOptionsTotal={discountableOptionsTotal}
             nonDiscountableOptionsTotal={nonDiscountableOptionsTotal}
             serviceOptionsTotal={customServiceOptionsPriceTotal}
             discountMode={discountMode}
             setDiscountMode={setDiscountMode}
             customDiscountPctRaw={customDiscountPctRaw}
             setCustomDiscountPctRaw={setCustomDiscountPctRaw}
             isDealerOffer={isDealerOffer}
             offerDiscountPercentage={offerDiscountPercentage}
             suggestedDiscountPct={suggestedDiscountPct}
             suggestedDiscountConfidence={suggestedDiscountConfidence}
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
             wiborPct={wiborPct}
             setWiborPct={setWiborPct}
             marginPct={marginPct}
             setMarginPct={setMarginPct}
             pricingMarginPct={pricingMarginPct}
             setPricingMarginPct={setPricingMarginPct}
             initialDepositPct={initialDepositPct}
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
             tireCostCorrection={tireCostCorrection}
             setTireCostCorrection={setTireCostCorrection}
             rimDiameter={rimDiameter}
             setRimDiameter={setRimDiameter}
             // Service cost type
             serviceCostType={serviceCostType}
             setServiceCostType={setServiceCostType}
             // Vehicle vintage & metalic
             vehicleVintage={vehicleVintage}
             setVehicleVintage={setVehicleVintage}
             isMetalic={isMetalic}
             setIsMetalic={setIsMetalic}
             isMetalicAutoDetected={autoDetectMetalic()}
             hookAutoDetected={(vehicle.synthesis_data as any)?.card_summary?.has_tow_hook === true}
             vintageAutoDetected={(vehicle.synthesis_data as any)?.card_summary?.is_current_year_vehicle != null}
             // Price context for czynsz inicjalny calculations
             activeFinalPriceForDeposit={activeFinalPriceNet}
             crossCardAlerts={crossCardAlerts}
             paramPreview={paramPreview}
             controlCenter={controlCenter}
          />

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

          <div className="mt-6 flex flex-col gap-3 pt-4 border-t border-slate-200">
             <VehicleActionButtons
               vehicle={vehicle}
               isSavingSetup={isSavingSetup}
               handleSaveSetup={() => handleSaveSetup(activeDiscountPct, activeFinalPriceNet, catalogBasePriceNet)}
               wiborPct={wiborPct}
               marginPct={marginPct}
               pricingMarginPct={pricingMarginPct}
               initialDepositPct={initialDepositPct}
               otherServiceCosts={otherServiceCosts}
               expressPaysInsurance={expressPaysInsurance}
               replacementCar={replacementCar}
               gpsRequired={gpsRequired}
               includeServicing={includeServicing}
               hookInstallation={hookInstallation}
               tireClass={tireClass}
               tireCountMode={tireCountMode}
               tireCostCorrectionEnabled={tireCostCorrectionEnabled}
               tireCostCorrection={tireCostCorrection}
               rimDiameter={rimDiameter}
               serviceCostType={serviceCostType}
               vehicleVintage={vehicleVintage}
               isMetalic={isMetalic}
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


              {isViewerOpen && vehicle.raw_pdf_url && (
                <div className="w-full h-full xl:w-1/2 p-2 border-l border-slate-200 mt-4 rounded-lg">
                  <PDFViewerFrame url={vehicle.raw_pdf_url} />
                </div>
              )}
            </div>

            {activeKalkulacjaId && activeKalkulacjaNumer && (
              <div id={`vehicle-matrix-${vehicle.id}`}>
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



