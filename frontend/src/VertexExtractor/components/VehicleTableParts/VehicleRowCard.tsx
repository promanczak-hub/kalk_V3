import { useState, useEffect, useMemo, useCallback } from "react";
import { Database, ExternalLink, Loader2, Wand2, X, AlertTriangle } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView, ModificationEffect, HomologationResponse } from "../../types";
import { parsePriceToNumber } from "./PriceDualFormat";
import { VehicleBaseInfo } from "./VehicleBaseInfo";
import type { MappedData } from "./VehicleBaseInfo";
import { VehicleFinancialOptions } from "./VehicleFinancialOptions";
// VehicleServiceIntervals removed — service cost uses normatywny_przebieg_mc floor
import { DocumentViewerFrame } from "./PDFViewerFrame";
import type { ExtractedServiceOption } from "../../../components/Calculator/ServiceOptionsManager";
import { BrochureBuilderModal } from "../brochure/BrochureBuilderModal";
import { VehicleSummaryCard } from "./VehicleSummaryCard";
import { VehicleEquipmentCard } from "./VehicleEquipmentCard";
import { VehicleFeaturesCard } from "./VehicleFeaturesCard";
import { RentalRatesMiniMatrix } from "./RentalRatesMiniMatrix";
import type { DiscountAlert } from "../../hooks/useDiscountAlerts";

interface VehicleRowCardProps {
  vehicle: FleetVehicleView;
  handleOpenSavedJson: (id: string, titleName: string) => void;
  onRefresh: () => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  crossCardAlerts?: DiscountAlert[];
}

export function VehicleRowCard({
  vehicle,
  handleOpenSavedJson,
  onRefresh,
  isSelected = false,
  onToggleSelect,
  crossCardAlerts = [],
}: VehicleRowCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [overridePrompt, setOverridePrompt] = useState("");
  const [isOverriding, setIsOverriding] = useState(false);

  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [isBrochureModalOpen, setIsBrochureModalOpen] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [brochureData, setBrochureData] = useState<any | null>(null);
  const [brochureImages, setBrochureImages] = useState<string[]>([]);
  const [isGeneratingBrochure, setIsGeneratingBrochure] = useState(false);

  // Save Setup state
  const [isSavingSetup, setIsSavingSetup] = useState(false);
  const [isSavingFields, setIsSavingFields] = useState(false);
  const [isRemappingClassification, setIsRemappingClassification] = useState(false);

  // Direct save: patch card_summary JSON + top-level columns
  const handleDirectSave = async (fields: Record<string, string>) => {
    setIsSavingFields(true);
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      if (!updatedJson.card_summary) updatedJson.card_summary = {};

      // Map of field keys that go into card_summary JSON
      const cardSummaryKeys = new Set([
        "trim_level", "body_style", "vehicle_class", "powertrain",
        "fuel", "transmission", "wheels", "emissions", "exterior_color",
        "configuration_code", "number_of_seats",
      ]);

      // Top-level column updates
      const columnUpdates: Record<string, unknown> = {};

      for (const [key, value] of Object.entries(fields)) {
        if (cardSummaryKeys.has(key)) {
          updatedJson.card_summary[key] = value;
        }
        if (key === "brand" || key === "model") {
          columnUpdates[key] = value;
        }
        if (key === "offer_number") {
          columnUpdates.offer_number = value;
        }
        if (key === "configuration_code") {
          updatedJson.configuration_code = value;
        }
      }

      columnUpdates.synthesis_data = updatedJson;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update(columnUpdates)
        .eq("id", vehicle.id);

      if (error) throw error;
      onRefresh();
    } catch (err) {
      console.error("Error saving vehicle fields", err);
      alert("B\u0142\u0105d zapisu: " + (err instanceof Error ? err.message : "Nieznany b\u0142\u0105d"));
    } finally {
      setIsSavingFields(false);
    }
  };

  // Re-run Flash classification (SAMAR, engine, service class)
  const handleRemapClassification = async () => {
    if (!vehicle.synthesis_data) return;
    setIsRemappingClassification(true);
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/api/extract/remap-classification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ original_json: vehicle.synthesis_data }),
      });

      if (!res.ok) throw new Error("B\u0142\u0105d klasyfikacji");
      const data = await res.json();

      // Save the new mapped data to Supabase
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      updatedJson.mapped_ai_data = data;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData(data);
      onRefresh();
    } catch (err) {
      console.error("Remap classification error", err);
      alert("B\u0142\u0105d przeliczania klasyfikacji: " + (err instanceof Error ? err.message : "Nieznany b\u0142\u0105d"));
    } finally {
      setIsRemappingClassification(false);
    }
  };


  // Financial parameters (defaults from control_center)
  const [wiborPct, setWiborPct] = useState<number>(5.85);
  const [marginPct, setMarginPct] = useState<number>(2.0);
  const [pricingMarginPct, setPricingMarginPct] = useState<number>(15.0);
  const [depreciationPct, setDepreciationPct] = useState<number | null>(null);
  const [initialDepositPct, setInitialDepositPct] = useState<number>(0);
  const [otherServiceCosts, setOtherServiceCosts] = useState<number>(0);

  // Toggles
  const [expressPaysInsurance, setExpressPaysInsurance] = useState(true);
  const [replacementCar, setReplacementCar] = useState(true);
  const [gpsRequired, setGpsRequired] = useState(true);
  const [includeServicing, setIncludeServicing] = useState(true);
  const [hookInstallation, setHookInstallation] = useState(() => {
    const cs = (vehicle.synthesis_data as any)?.card_summary;
    return cs?.has_tow_hook === true;
  });

  // Tire parameters
  const [tireClass, setTireClass] = useState<string>("Medium");
  const [tireCountMode, setTireCountMode] = useState<string>("auto");
  const [tireCostCorrectionEnabled, setTireCostCorrectionEnabled] = useState(true);
  const [tireCostCorrection, setTireCostCorrection] = useState<number>(0);
  const [rimDiameter, setRimDiameter] = useState<number | null>(() => {
    const wheels = vehicle.wheels || "";
    const match = wheels.match(/(\d{2})/);
    return match ? parseInt(match[1], 10) : null;
  });

  // Service cost type (ASO / nonASO)
  const [serviceCostType, setServiceCostType] = useState<"ASO" | "nonASO">("ASO");

  // Vehicle vintage (bieżący / ubiegły rocznik)
  const [vehicleVintage, setVehicleVintage] = useState<"current" | "previous">(() => {
    const cs = (vehicle.synthesis_data as any)?.card_summary;
    if (cs?.is_current_year_vehicle === false) return "previous";
    return "current";
  });

  // Metalik auto-detection: keyword matching overrides AI errors
  const autoDetectMetalic = (): boolean => {
    const cs = (vehicle.synthesis_data as any)?.card_summary;
    // Step 1: keyword matching on exterior_color (highest priority — catches AI errors)
    const color = (vehicle.exterior_color || "").toLowerCase();
    const metallicKeywords = ["metalic", "metalik", "metallic", "metalizow", "perłowy", "pearl", "mica", "xirallic", "special efekt", "dwuwarstwow"];
    if (metallicKeywords.some(kw => color.includes(kw))) return true;
    const nonMetallicKeywords = ["solido", "uni ", "akrylow", "jednowarstwow"];
    if (nonMetallicKeywords.some(kw => color.includes(kw))) return false;
    // Step 2: AI flag (only if keywords inconclusive)
    if (cs?.is_metalic_paint === true) return true;
    if (cs?.is_metalic_paint === false) return false;
    // Step 3: no data — default to false
    return false;
  };
  const [isMetalic, setIsMetalic] = useState<boolean>(autoDetectMetalic());

  // Fetch control_center defaults
  useEffect(() => {
    const fetchDefaults = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const resp = await fetch(`${baseUrl}/api/control-center`);
        if (resp.ok) {
          const settings = await resp.json();
          if (settings.default_wibor) setWiborPct(settings.default_wibor);
          if (settings.bank_spread) setMarginPct(settings.bank_spread);
          if (settings.default_ltr_margin) setPricingMarginPct(settings.default_ltr_margin);
          // depreciation_pct auto-calculated by backend — do not override
        }
      } catch (e) {
        console.error("Failed to fetch control_center defaults", e);
      }
    };
    fetchDefaults();
  }, []);

  // Restore saved calculator_setup from synthesis_data on load
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setup = (vehicle.synthesis_data as any)?.calculator_setup;
    if (!setup) return;
    // Financial params
    if (setup.financial_params) {
      const fp = setup.financial_params;
      if (fp.wibor_pct != null) setWiborPct(fp.wibor_pct);
      if (fp.margin_pct != null) setMarginPct(fp.margin_pct);
      if (fp.pricing_margin_pct != null) setPricingMarginPct(fp.pricing_margin_pct);
      if (fp.depreciation_pct != null) setDepreciationPct(fp.depreciation_pct);
      if (fp.initial_deposit_pct != null) setInitialDepositPct(fp.initial_deposit_pct);
      if (fp.other_service_costs != null) setOtherServiceCosts(fp.other_service_costs);
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
      if (tp.rim_diameter != null) setRimDiameter(tp.rim_diameter);
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
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.id]);





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
       // @ts-ignore
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

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [homologationResult, setHomologationResult] = useState<HomologationResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    const verifyHomologation = async () => {
      try {
        const mappedData = vehicle.synthesis_data?.mapped_ai_data as MappedData | undefined;
        // Default base payload if missing (for now using 1000kg as fallback or extracting from real schema later)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${baseUrl}/api/homologation/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) return;
        const data = await res.json();
        if (mounted) {
          setHomologationResult(data);
        }
      } catch {
        // silently fail verification
      }
    };

    const timeout = setTimeout(verifyHomologation, 600);
    return () => {
      mounted = false;
      clearTimeout(timeout);
    };
  }, [customServiceOptions, vehicle.id, vehicle.synthesis_data]);

  const [isSavingServices, setIsSavingServices] = useState(false);

  const handleSaveSetup = async () => {
    setIsSavingSetup(true);
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      updatedJson.calculator_setup = {
        financial_params: {
          wibor_pct: wiborPct,
          margin_pct: marginPct,
          pricing_margin_pct: pricingMarginPct,
          depreciation_pct: null,  // auto-calculated by backend per cell
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
        saved_at: new Date().toISOString(),
      };

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;
    } catch (err) {
      console.error("Error saving calculator setup", err);
      alert("Błąd podczas zapisu setupu: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    } finally {
      setIsSavingSetup(false);
    }
  };

  const handleSaveAllOptions = async () => {
    setIsSavingServices(true);
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

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

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;
      onRefresh();
    } catch (err) {
      console.error("Error saving options", err);
      alert("Błąd podczas zapisu opcji: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    } finally {
      setIsSavingServices(false);
    }
  };

  const [localMappedData, setLocalMappedData] = useState<MappedData | null>(null);
  const [isMapping, setIsMapping] = useState(false);

  const serverMappedData = vehicle.synthesis_data?.mapped_ai_data as MappedData | undefined;
  const mappedData = localMappedData || serverMappedData;

  // Extract SAMAR candidates for reranking dropdown
  const samarCandidates: { klasa: string; confidence: number }[] =
    ((vehicle.synthesis_data?.mapped_ai_data as MappedData & { samar_candidates?: { klasa: string; confidence: number }[] })?.samar_candidates) || [];

  // Extract Engine candidates for reranking dropdown
  const engineCandidates: { klasa: string; confidence: number }[] =
    ((vehicle.synthesis_data?.mapped_ai_data as MappedData & { engine_candidates?: { klasa: string; confidence: number }[] })?.engine_candidates) || [];

  // ── Readiness Check ──────────────────────────────────────────────
  interface ReadinessCheck {
    param: string;
    status: string;
    value: string;
  }
  interface ReadinessResult {
    overall_status: "ready" | "partial" | "not_ready";
    samar_class_id: number | null;
    fuel_type_id: number | null;
    checks: ReadinessCheck[];
    critical_count: number;
    warning_count: number;
    resolve_error?: string;
    body_match?: {
      matched_name: string | null;
      vehicle_class: string | null;
      score: number;
      match_method: string;
      raw_input: string;
    };
  }

  const [readinessResult, setReadinessResult] = useState<ReadinessResult | null>(null);

  const fetchReadiness = useCallback(async () => {
    const samarName = mappedData?.samar_category;
    const engineName = mappedData?.fuel;
    if (!samarName || !engineName) {
      setReadinessResult(null);
      return;
    }
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const params = new URLSearchParams({
        samar_class_name: samarName,
        engine_name: engineName,
        brand_name: vehicle.brand || "",
      });
      // Pass body_type if available
      if (vehicle.body_style) {
        params.set("body_type_name", vehicle.body_style);
      }
      // Pass paint type based on isMetalic toggle or exterior color info
      const paintTypeName = isMetalic ? "Metalizowany" : "Niemetalizowany";
      params.set("paint_type_name", paintTypeName);

      const res = await fetch(`${baseUrl}/api/readiness-check?${params}`);
      if (!res.ok) throw new Error("Readiness check failed");
      const data: ReadinessResult = await res.json();
      setReadinessResult(data);
    } catch (err) {
      console.error("Readiness check error:", err);
      setReadinessResult(null);
    }
  }, [mappedData?.samar_category, mappedData?.fuel, vehicle.brand, vehicle.body_style, isMetalic]);

  useEffect(() => {
    fetchReadiness();
  }, [fetchReadiness]);

  // ── Param Preview (live LinkedIndicator data) ─────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [paramPreview, setParamPreview] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [controlCenter, setControlCenter] = useState<any>(null);

  // Fetch control center once on mount (global params)
  useEffect(() => {
    const fetchCC = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${baseUrl}/api/control-center`);
        if (res.ok) {
          const data = await res.json();
          setControlCenter(data);
        }
      } catch {
        // silently fail
      }
    };
    fetchCC();
  }, []);

  // Fetch param preview reactively when params change
  const fetchParamPreview = useCallback(async () => {
    const classId = readinessResult?.samar_class_id;
    const engineId = readinessResult?.fuel_type_id;
    if (!classId || !engineId) {
      setParamPreview(null);
      return;
    }
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const params = new URLSearchParams({
        samar_class_id: String(classId),
        engine_type_id: String(engineId),
        power_band: "MID",
        service_type: serviceCostType,
        tire_class: tireClass,
        vehicle_vintage: vehicleVintage,
        is_metalic: String(isMetalic),
      });
      if (rimDiameter) params.set("rim_diameter", String(rimDiameter));
      const res = await fetch(`${baseUrl}/api/param-preview?${params}`);
      if (res.ok) {
        setParamPreview(await res.json());
      }
    } catch {
      // silently fail
    }
  }, [readinessResult?.samar_class_id, readinessResult?.fuel_type_id, serviceCostType, tireClass, rimDiameter, vehicleVintage, isMetalic]);

  useEffect(() => {
    fetchParamPreview();
  }, [fetchParamPreview]);

  // Extract drive type from card_summary
  const DRIVE_TYPE_MAP: Record<string, string> = {
    "Napęd FWD": "4x2 (FWD)", "Napęd RWD": "4x2 (RWD)", "Napęd AWD": "4x4 (AWD)",
    "FWD": "4x2 (FWD)", "RWD": "4x2 (RWD)", "AWD": "4x4 (AWD)",
  };
  const rawDriveType = (vehicle.synthesis_data as Record<string, Record<string, unknown>> | undefined)
    ?.card_summary?.drive_type as string | undefined;
  const detectedDriveType = rawDriveType ? (DRIVE_TYPE_MAP[rawDriveType] ?? rawDriveType) : "";
  const driveType = mappedData?.drive_type || detectedDriveType;

  const handleSamarCategoryChange = async (newCategory: string) => {
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

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
      alert("Błąd zapisu kategorii SAMAR: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleEngineCategoryChange = async (newCategory: string) => {
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

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
      alert("Błąd zapisu kategorii Silnika: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleDriveTypeChange = async (newDriveType: string) => {
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

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
      alert("Błąd zapisu napędu: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

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

  // ── Processing stages for progress stepper ──
  const PROCESSING_STAGES = [
    { key: "uploading", label: "Upload pliku do chmury" },
    { key: "detecting_vehicles", label: "Wykrywanie pojazdów w dokumencie" },
    { key: "extracting_twin", label: "Bliźniak cyfrowy (Gemini Pro)" },
    { key: "generating_summary", label: "Generowanie podsumowania" },
    { key: "matching_discounts", label: "Dopasowywanie rabatów" },
    { key: "mapping_data", label: "Mapowanie danych AI" },
  ];

  // Match multi-vehicle dynamic statuses like "extracting_twin_2_of_5"
  const rawStatus = vehicle.verification_status || "";
  const isMultiTwinStatus = rawStatus.startsWith("extracting_twin_");
  const normalizedStatus = isMultiTwinStatus ? "extracting_twin" : rawStatus;

  const processingStatuses = new Set([
    "processing", "uploading", "detecting_vehicles", "extracting_twin",
    "generating_summary", "matching_discounts", "mapping_data",
  ]);

  const handleManualOverride = async (promptOverride?: string) => {
    const finalPrompt = promptOverride || overridePrompt;
    if (!finalPrompt.trim()) return;
    setIsOverriding(true);
    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);

      const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/api/extract/manual-override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_json: vehicle.synthesis_data,
          user_prompt: finalPrompt,
        }),
      });

      if (!res.ok) {
        throw new Error("Błąd z odpowiedzi serwera.");
      }

      const updatedJson = await res.json();

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

  const handleServiceOptionExtracted = async (extractedOption: ExtractedServiceOption) => {
    try {
      const newOption = {
        id: crypto.randomUUID(),
        name: extractedOption.name,
        category: "Opcja Serwisowa",
        price_net: extractedOption.net_price,
        effects: extractedOption.effects || undefined
      };

      setCustomServiceOptions(prev => [...prev, newOption]);

      if (extractedOption.effects) {
        const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
        const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
        if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
        if (extractedOption.effects.override_samar_class) {
           updatedJson.mapped_ai_data.samar_category = extractedOption.effects.override_samar_class;
        }
        if (extractedOption.effects.override_homologation) {
           updatedJson.mapped_ai_data.vehicle_type = extractedOption.effects.override_homologation;
        }
      }

      if (extractedOption.effects && (extractedOption.effects.override_samar_class || extractedOption.effects.override_homologation)) {
        const { createClient } = await import("@supabase/supabase-js");
        const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
        const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
        const supabase = createClient(supabaseUrl, supabaseKey);

        const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
        const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

        if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
        if (extractedOption.effects.override_samar_class) {
           updatedJson.mapped_ai_data.samar_category = extractedOption.effects.override_samar_class;
        }
        if (extractedOption.effects.override_homologation) {
           updatedJson.mapped_ai_data.vehicle_type = extractedOption.effects.override_homologation;
        }

        const { error } = await supabase
          .from("vehicle_synthesis")
          .update({ synthesis_data: updatedJson })
          .eq("id", vehicle.id);

        if (error) throw error;
        onRefresh();
      }
    } catch (err) {
      console.error("Error saving extracted service option", err);
      alert("Błąd podczas zapisu opcji: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const [discountMode, setDiscountMode] = useState<"offer" | "suggested" | "custom">("offer");
  const [customDiscountPctRaw, setCustomDiscountPctRaw] = useState<string | number>("");

  const customDiscountPct = Number(customDiscountPctRaw) || 0;

  const basePrice = parsePriceToNumber(vehicle.base_price);
  const optionsPrice = parsePriceToNumber(vehicle.options_price);
  const totalCatalogPrice = basePrice + optionsPrice;

  const offerFinalPrice = parsePriceToNumber(vehicle.final_price_pln);
  const hasOfferFinalPrice = Boolean(
    vehicle.final_price_pln &&
    vehicle.final_price_pln !== "Brak" &&
    vehicle.final_price_pln !== vehicle.base_price
  );
  const isDealerOffer = Boolean(
    hasOfferFinalPrice && offerFinalPrice > 0 && offerFinalPrice < totalCatalogPrice - 1.0
  );
  
  const cardSummary = vehicle.synthesis_data?.card_summary as Record<string, unknown> | undefined;
  const parsedOfferDiscountPct = cardSummary?.offer_discount_pct;

  const offerDiscountPercentage = parsedOfferDiscountPct
    ? Number(parsedOfferDiscountPct)
    : isDealerOffer && totalCatalogPrice > 0
      ? Number((((totalCatalogPrice - offerFinalPrice) / totalCatalogPrice) * 100).toFixed(1))
      : 0;

  const suggestedDiscountPct = vehicle.suggested_discount_pct || 0;
  const suggestedDiscountConfidence = vehicle.suggested_discount_confidence || 0;

  let activeDiscountPct = 0;
  let activeFinalPrice = totalCatalogPrice;

  // We need option splits to properly compute discounted price
  // These are in netto; convert to source domain below if needed
  const factoryOptionsPriceTotal = customFactoryOptions.reduce((acc, curr) => acc + curr.price_net, 0);
  const customServiceOptionsPriceTotal = customServiceOptions.reduce((acc, curr) => acc + curr.price_net, 0);

  const dynamicTotalOptionsPrice = factoryOptionsPriceTotal + customServiceOptionsPriceTotal;

  // Split factory options into discountable / non-discountable
  const discountableOptionsTotal = customFactoryOptions
    .filter(opt => !opt.no_discount)
    .reduce((acc, curr) => acc + curr.price_net, 0);
  const nonDiscountableOptionsTotal = customFactoryOptions
    .filter(opt => opt.no_discount)
    .reduce((acc, curr) => acc + curr.price_net, 0);

  // Detect source price domain for proper netto/brutto-aware calculations
  const isSourceNetto = vehicle.base_price?.toLowerCase().includes("netto") ?? false;
  // Options are always stored as price_net - convert non-discountable to source domain
  const nonDiscInSourceDomain = isSourceNetto
    ? nonDiscountableOptionsTotal
    : nonDiscountableOptionsTotal * 1.23;
  const serviceInSourceDomain = isSourceNetto
    ? customServiceOptionsPriceTotal
    : customServiceOptionsPriceTotal * 1.23;
  // discountableBase = totalCatalogPrice minus non-discountable minus service opts
  const discountableBase = totalCatalogPrice - nonDiscInSourceDomain - serviceInSourceDomain;

  if (discountMode === "offer" && isDealerOffer) {
    activeDiscountPct = offerDiscountPercentage;
    activeFinalPrice = offerFinalPrice;
  } else if (discountMode === "suggested") {
    activeDiscountPct = suggestedDiscountPct;
    // Discount only the discountable portion (base + discountable opts)
    activeFinalPrice =
      discountableBase * (1 - suggestedDiscountPct / 100)
      + nonDiscInSourceDomain
      + serviceInSourceDomain;
  } else if (discountMode === "custom") {
    activeDiscountPct = customDiscountPct;
    activeFinalPrice =
      discountableBase * (1 - customDiscountPct / 100)
      + nonDiscInSourceDomain
      + serviceInSourceDomain;
  }

  const formatCalculatedPrice = (val: number) => {
      if (val === 0) return "Brak";
      const isNetto = vehicle.base_price?.toLowerCase().includes("netto");
      return `${val.toFixed(2)} PLN ${isNetto ? 'netto' : 'brutto'}`;
  };



  const isProcessing = processingStatuses.has(normalizedStatus);

  // Cancelled vehicles should not render at all (cancel = delete)
  if (vehicle.verification_status === "cancelled") {
    return null;
  }

  if (vehicle.verification_status === "error") {
    const handleDeleteError = async () => {
      if (!window.confirm("Czy na pewno chcesz usunąć ten wpis z błędem?")) return;
      try {
        const { createClient } = await import("@supabase/supabase-js");
        const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
        const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
        const supabase = createClient(supabaseUrl, supabaseKey);
        
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
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${baseUrl}/api/cancel-processing`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ vehicle_id: vehicle.id }),
        });
        if (!res.ok) throw new Error("Cancel failed");
        // Cancel = delete — remove the vehicle after stopping processing
        window.dispatchEvent(new CustomEvent('deleteVehicle', { detail: { vehicleId: vehicle.id } }));
      } catch (err) {
        console.error("Cancel error, attempting direct Supabase cleanup:", err);
        try {
            // Plan B: bezpośrednie skasowanie wiersza przez Supabase JS jeśli backend leży
            const { createClient } = await import("@supabase/supabase-js");
            const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
            const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
            const supabase = createClient(supabaseUrl, supabaseKey);
            
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
      data-vehicle-id={vehicle.id}
      className={cn(
        "bg-white rounded-xl border transition-all duration-200 shadow-sm overflow-hidden group hover:shadow-md",
        isExpanded ? "border-blue-300 ring-4 ring-blue-50/50" : "border-slate-200 hover:border-blue-200"
      )}
    >
      <VehicleBaseInfo 
        vehicle={vehicle}
        mappedData={mappedData}
        isExpanded={isExpanded}
        onToggleExpand={() => setIsExpanded(!isExpanded)}
        activeFinalPrice={activeFinalPrice}
        totalCatalogPrice={totalCatalogPrice}
        formatCalculatedPrice={formatCalculatedPrice}
        samarCandidates={samarCandidates}
        onSamarCategoryChange={handleSamarCategoryChange}
        engineCandidates={engineCandidates}
        onEngineCategoryChange={handleEngineCategoryChange}
        driveType={driveType}
        onDriveTypeChange={handleDriveTypeChange}
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
            <RentalRatesMiniMatrix
              vehicle={vehicle}
              basePriceNet={toNettoAware(basePrice, vehicle.base_price || undefined)}
              discountPct={activeDiscountPct}
              defaultMarginPct={pricingMarginPct}
              wiborPct={wiborPct}
              marginPct={marginPct}
              depreciationPct={depreciationPct ?? 0}
              initialDepositPct={initialDepositPct}
              replacementCar={replacementCar}
              gpsRequired={gpsRequired}
              hookInstallation={hookInstallation}
              includeServicing={includeServicing}
              tireClass={tireClass}
              tireCountMode={tireCountMode}
              tireCostCorrectionEnabled={tireCostCorrectionEnabled}
              tireCostCorrection={tireCostCorrection}
              rimDiameter={rimDiameter}
              serviceCostType={serviceCostType}
              vehicleVintage={vehicleVintage}
              isMetalic={isMetalic}
              factoryOptions={customFactoryOptions.map((o) => ({
                name: o.name,
                price_net: o.price_net,
                no_discount: (o as any).no_discount || false,
              }))}
              serviceOptions={customServiceOptions.map((o) => ({
                name: o.name,
                price_net: o.price_net,
                include_in_wr: o.include_in_wr || false,
              }))}
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
            <VehicleFeaturesCard vehicleId={vehicle.id} />
          </div>

          <VehicleFinancialOptions 
             vehicle={vehicle}
             totalCatalogPrice={totalCatalogPrice}
             activeFinalPrice={activeFinalPrice}
             dynamicTotalOptionsPrice={dynamicTotalOptionsPrice}
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
             handleServiceOptionExtracted={handleServiceOptionExtracted}
             // Financial parameters
             wiborPct={wiborPct}
             setWiborPct={setWiborPct}
             marginPct={marginPct}
             setMarginPct={setMarginPct}
             pricingMarginPct={pricingMarginPct}
             setPricingMarginPct={setPricingMarginPct}
             depreciationPct={depreciationPct ?? 0}
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
             activeFinalPriceForDeposit={activeFinalPrice}
             crossCardAlerts={crossCardAlerts}
             paramPreview={paramPreview}
             controlCenter={controlCenter}
          />



          <div className="mt-6 flex flex-col items-end gap-3 pt-4 border-t border-slate-200">
             <div className="flex justify-end items-center gap-3">
               <button
                 onClick={async (e) => {
                   e.stopPropagation();
                   try {
                     // 1. Save setup to synthesis_data first
                     await handleSaveSetup();

                     // 2. Create kalkulacja
                     const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
                     const resp = await fetch(`${baseUrl}/api/kalkulacje`, {
                       method: "POST",
                       headers: { "Content-Type": "application/json" },
                       body: JSON.stringify({ 
                          stan_json: {
                            ...(vehicle.synthesis_data || {}),
                            financial_params: {
                              wibor_pct: wiborPct,
                              margin_pct: marginPct,
                              pricing_margin_pct: pricingMarginPct,
                              depreciation_pct: null,  // auto-calculated by backend per cell
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

                     const params = new URLSearchParams();
                     params.set('id', data.id);
                     params.set('kalkulacja', numerKalkulacji);
                     params.set('aktywnyRabatProcent', activeDiscountPct.toString());
                     params.set('aktywnaCenaKoncowa', activeFinalPrice.toString());

                     window.dispatchEvent(
                       new CustomEvent('switchTab', {
                         detail: { tabIndex: 2, urlParams: params },
                       })
                     );
                   } catch (err) {
                     console.error("Błąd tworzenia kalkulacji:", err);
                     alert("Nie udało się utworzyć kalkulacji. Sprawdź logi serwera.");
                   }
                 }}
                 disabled={isSavingSetup}
                 className="flex items-center text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
               >
                 {isSavingSetup ? (
                   <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
                 ) : (
                   <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                 )}
                 {isSavingSetup ? "Zapisywanie setupu..." : "Zrób kalkulację"}
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
                   onClick={async (e) => {
                     e.stopPropagation();
                     // Jeśli mamy już pobrane dane z tego cyklu, od razu otwieramy 
                     if (brochureData) {
                       setIsBrochureModalOpen(true);
                       return;
                     }
                     // Jeśli nie - ładujemy do skutku i blokujemy przycisk
                     setIsGeneratingBrochure(true);
                     try {
                        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
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
                   }}
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
                 <button
                   onClick={(e) => {
                     e.stopPropagation();
                     if (vehicle.raw_pdf_url) setIsViewerOpen(!isViewerOpen);
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
                     onClick={() => handleManualOverride()}
                     disabled={isOverriding || !overridePrompt.trim()}
                     className="px-4 py-2 bg-emerald-600 text-white rounded-md font-medium text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center shadow-sm transition-colors"
                   >
                     {isOverriding ? <Loader2 className="w-4 h-4 animate-spin mr-1.5" /> : null}
                     {isOverriding ? "Korygowanie..." : "Zastosuj"}
                   </button>
                 </div>
                 <p className="text-xs text-slate-500 mt-2">
                   Algorytm chirurgicznie zedytuje wyłącznie zlecane parametry w obrębie Cyfrowego Bliźniaka, zachowując 100% spójności reszty dokumentu. Zmiana widoczna będzie po odświeżeniu.
                 </p>
               </div>
             )}

              {isViewerOpen && vehicle.raw_pdf_url && (
                 <DocumentViewerFrame 
                    rawDocUrl={vehicle.raw_pdf_url} 
                    brand={vehicle.brand || "?"} 
                    model={vehicle.model || "?"} 
                 />
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
