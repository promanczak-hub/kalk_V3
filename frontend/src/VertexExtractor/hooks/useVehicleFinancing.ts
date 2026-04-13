import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabaseClient";
import type { FleetVehicleView } from "../types";
import { parsePriceToNumber } from "../components/VehicleTableParts/PriceDualFormat";
import type { ControlCenterSettings } from "../../types";

export function useVehicleFinancing(
  vehicle: FleetVehicleView,
  autoDetectMetalic: () => boolean,
  setCatalogBasePriceNet: (val: number) => void,
  globalSettings?: ControlCenterSettings | null
) {
  // Financial parameters
  // Financial parameters - strictly null by default, wait for globalSettings or existing setup.
  const [wiborPct, setWiborPct] = useState<number | null>(globalSettings?.default_wibor ?? null);
  const [marginPct, setMarginPct] = useState<number | null>(globalSettings?.bank_spread ?? null);
  const [pricingMarginPct, setPricingMarginPct] = useState<number | null>(globalSettings?.default_ltr_margin ?? null);
  const [initialDepositPct, setInitialDepositPct] = useState<number>(0);
  const [otherServiceCosts, setOtherServiceCosts] = useState<number>(0);

  // Toggles
  const [expressPaysInsurance, setExpressPaysInsurance] = useState(true);
  const [replacementCar, setReplacementCar] = useState(true);
  const [gpsRequired, setGpsRequired] = useState(true);
  const [includeServicing, setIncludeServicing] = useState(true);
  const [includeTires, setIncludeTires] = useState(true);
  const [hookInstallation, setHookInstallation] = useState(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cs = (vehicle.synthesis_data as any)?.card_summary;
    return cs?.has_tow_hook === true;
  });
  const [addSalesPrep, setAddSalesPrep] = useState(true);
  const [salesPrepCorrection, setSalesPrepCorrection] = useState<number>(0);

  // Tire parameters
  const [tireClass, setTireClass] = useState<string>("Medium");
  const [tireCountMode, setTireCountMode] = useState<string>("auto");
  const [tireCostCorrectionEnabled, setTireCostCorrectionEnabled] = useState(false);
  const [tireCostCorrectionMap, setTireCostCorrectionMap] = useState<Record<string, number>>({});
  const [rimDiameter, setRimDiameter] = useState<number | null>(() => {
    const wheels = vehicle.wheels || "";
    const match = wheels.match(/(\d{2})/);
    return match ? parseInt(match[1], 10) : null;
  });

  // Service cost type
  const [serviceCostType, setServiceCostType] = useState<"ASO" | "nonASO">("ASO");

  // Vehicle vintage
  const [vehicleVintage, setVehicleVintage] = useState<"current" | "previous">(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cs = (vehicle.synthesis_data as any)?.card_summary;
    if (cs?.is_current_year_vehicle === false) return "previous";
    return "current";
  });

  // Paint Category (1: Niemetalizowany, 2: Metalizowany, 3: Perłowy)
  const [paintCategoryId, setPaintCategoryId] = useState<number>(() => {
    return autoDetectMetalic() ? 2 : 1;
  });

  // Save State
  const [isSavingSetup, setIsSavingSetup] = useState(false);

  // Restore saved calculator_setup
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setup = (vehicle.synthesis_data as any)?.calculator_setup;

    if (!setup) {
      if (globalSettings) {
        setWiborPct(globalSettings.default_wibor ?? null);
        setMarginPct(globalSettings.bank_spread ?? null);
      }
      setPaintCategoryId(autoDetectMetalic() ? 2 : 1);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cs = (vehicle.synthesis_data as any)?.card_summary;
      setHookInstallation(cs?.has_tow_hook === true);
      setVehicleVintage(cs?.is_current_year_vehicle === false ? "previous" : "current");

      const wheels = vehicle.wheels || "";
      const match = wheels.match(/(\d{2})/);
      if (match) setRimDiameter(parseInt(match[1], 10));

      const aiBase = parsePriceToNumber(vehicle.base_price);
      const pd = (vehicle.synthesis_data as any)?.card_summary?.price_domain;
      const isDomainNetto = pd === "netto" || (typeof pd === 'string' && pd.toLowerCase().includes("netto"));
      const isNetto = (typeof vehicle.base_price === 'string' && vehicle.base_price.toLowerCase().includes("netto")) || isDomainNetto;
      setCatalogBasePriceNet(isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100);
      return;
    }

    if (setup.financial_params) {
      const fp = setup.financial_params;
      
      // Zawsze nadpisuj WIBOR i Marżę Bankową aktualnymi wartościami globalnymi (nie dziedzicz starych)
      if (globalSettings) {
        setWiborPct(globalSettings.default_wibor ?? null);
        setMarginPct(globalSettings.bank_spread ?? null);
      }
      
      if (fp.pricing_margin_pct != null) setPricingMarginPct(fp.pricing_margin_pct);
      if (fp.initial_deposit_pct != null) setInitialDepositPct(fp.initial_deposit_pct);
      if (fp.other_service_costs != null) setOtherServiceCosts(fp.other_service_costs);
      if (fp.sales_prep_correction != null) setSalesPrepCorrection(fp.sales_prep_correction);
      else if (fp.korekta_kosztu_przygotowania != null) setSalesPrepCorrection(fp.korekta_kosztu_przygotowania);

      if (fp.catalog_base_price_net != null && fp.catalog_base_price_net > 0) {
        setCatalogBasePriceNet(fp.catalog_base_price_net);
      } else {
        const aiBase = parsePriceToNumber(vehicle.base_price);
        const csLocal = (vehicle.synthesis_data as any)?.card_summary;
        const isDomainNetto = csLocal?.price_domain === "netto" || (typeof csLocal?.price_domain === 'string' && csLocal.price_domain.toLowerCase().includes("netto"));
        const isNetto = (typeof vehicle.base_price === 'string' && vehicle.base_price.toLowerCase().includes("netto")) || isDomainNetto;
        setCatalogBasePriceNet(isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100);
      }
    } else {
      const aiBase = parsePriceToNumber(vehicle.base_price);
      const csLocal = (vehicle.synthesis_data as any)?.card_summary;
      const isDomainNetto = csLocal?.price_domain === "netto" || (typeof csLocal?.price_domain === 'string' && csLocal.price_domain.toLowerCase().includes("netto"));
      const isNetto = (typeof vehicle.base_price === 'string' && vehicle.base_price.toLowerCase().includes("netto")) || isDomainNetto;
      setCatalogBasePriceNet(isNetto ? aiBase : Math.round((aiBase / 1.23) * 100) / 100);
    }

    if (setup.toggles) {
      const t = setup.toggles;
      if (t.express_pays_insurance != null) setExpressPaysInsurance(t.express_pays_insurance);
      if (t.replacement_car != null) setReplacementCar(t.replacement_car);
      if (t.gps_required != null) setGpsRequired(t.gps_required);
      if (t.include_servicing != null) setIncludeServicing(t.include_servicing);
      if (t.include_tires != null) setIncludeTires(t.include_tires);
      if (t.hook_installation != null) setHookInstallation(t.hook_installation);
      if (t.add_sales_prep != null) setAddSalesPrep(t.add_sales_prep);
    }

    if (setup.tire_params) {
      const tp = setup.tire_params;
      if (tp.tire_class != null) setTireClass(tp.tire_class);
      if (tp.tire_count_mode != null) setTireCountMode(tp.tire_count_mode);
      if (tp.tire_cost_correction_enabled != null) setTireCostCorrectionEnabled(tp.tire_cost_correction_enabled);
      // Backward compat: stary scalar float → reset do pustej mapy
      if (tp.tire_cost_correction_map != null && typeof tp.tire_cost_correction_map === "object") {
        setTireCostCorrectionMap(tp.tire_cost_correction_map as Record<string, number>);
      } else {
        setTireCostCorrectionMap({});
      }
      if (tp.rim_diameter != null) setRimDiameter(tp.rim_diameter);
      else {
        const wheels = vehicle.wheels || "";
        const match = wheels.match(/(\d{2})/);
        if (match) setRimDiameter(parseInt(match[1], 10));
      }
    } else {
      const wheels = vehicle.wheels || "";
      const match = wheels.match(/(\d{2})/);
      if (match) setRimDiameter(parseInt(match[1], 10));
    }

    if (setup.service_cost_type) setServiceCostType(setup.service_cost_type);
    if (setup.vehicle_vintage) setVehicleVintage(setup.vehicle_vintage);

    if (setup.paint_category_id != null) {
      setPaintCategoryId(setup.paint_category_id);
    } else if (setup.is_metalic != null) {
      // Migration from legacy boolean
      const keywordDetected = autoDetectMetalic();
      const color = (vehicle.exterior_color || "").toLowerCase();
      const hasKeyword = [
        "metalic", "metalik", "metallic", "metalizow", "perłowy",
        "pearl", "mica", "xirallic", "special efekt", "dwuwarstwow"
      ].some(kw => color.includes(kw)) ||
      ["solido", "uni ", "akrylow", "jednowarstwow"].some(kw => color.includes(kw));
      
      const legacyVal = hasKeyword ? keywordDetected : setup.is_metalic;
      setPaintCategoryId(legacyVal ? 2 : 1);
    } else {
      setPaintCategoryId(autoDetectMetalic() ? 2 : 1);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.id, vehicle.synthesis_data, vehicle.exterior_color, vehicle.wheels, globalSettings]);

  const handleSaveSetup = async (activeDiscountPct: number, activeFinalPrice: number, catalogBasePriceNet: number) => {
    setIsSavingSetup(true);
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      updatedJson.calculator_setup = {
        financial_params: {
          wibor_pct: wiborPct,
          margin_pct: marginPct,
          pricing_margin_pct: pricingMarginPct,
          depreciation_pct: null,
          initial_deposit_pct: initialDepositPct,
          other_service_costs: otherServiceCosts,
          sales_prep_correction: salesPrepCorrection,
        },
        toggles: {
          express_pays_insurance: expressPaysInsurance,
          replacement_car: replacementCar,
          gps_required: gpsRequired,
          include_servicing: includeServicing,
          include_tires: includeTires,
          hook_installation: hookInstallation,
          add_sales_prep: addSalesPrep,
        },
        tire_params: {
          tire_class: tireClass,
          tire_count_mode: tireCountMode,
          tire_cost_correction_enabled: tireCostCorrectionEnabled,
          tire_cost_correction_map: tireCostCorrectionMap,
          rim_diameter: rimDiameter,
        },
        service_cost_type: serviceCostType,
        vehicle_vintage: vehicleVintage,
        paint_category_id: paintCategoryId,
        discount: {
          active_discount_pct: activeDiscountPct,
          active_final_price: activeFinalPrice,
        },
        catalog_base_price_net: catalogBasePriceNet,
        saved_at: new Date().toISOString(),
      };

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;
    } catch (err) {
      console.error("Error saving calculator setup", err);
      throw err;
    } finally {
      setIsSavingSetup(false);
    }
  };

  return {
    wiborPct, setWiborPct,
    marginPct, setMarginPct,
    pricingMarginPct, setPricingMarginPct,
    initialDepositPct, setInitialDepositPct,
    otherServiceCosts, setOtherServiceCosts,
    expressPaysInsurance, setExpressPaysInsurance,
    replacementCar, setReplacementCar,
    gpsRequired, setGpsRequired,
    includeServicing, setIncludeServicing,
    includeTires, setIncludeTires,
    hookInstallation, setHookInstallation,
    addSalesPrep, setAddSalesPrep,
    salesPrepCorrection, setSalesPrepCorrection,
    tireClass, setTireClass,
    tireCountMode, setTireCountMode,
    tireCostCorrectionEnabled, setTireCostCorrectionEnabled,
    tireCostCorrectionMap, setTireCostCorrectionMap,
    rimDiameter, setRimDiameter,
    serviceCostType, setServiceCostType,
    vehicleVintage, setVehicleVintage,
    paintCategoryId, setPaintCategoryId,
    isSavingSetup, handleSaveSetup
  };
}

