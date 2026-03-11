import { useState, useEffect } from "react";
import { supabase } from "../../../../lib/supabaseClient";
import type { FleetVehicleView } from "../../../types";
import { parsePriceToNumber } from "../components/VehicleTableParts/PriceDualFormat";

export function useVehicleFinancing(
  vehicle: FleetVehicleView,
  autoDetectMetalic: () => boolean,
  setCatalogBasePriceNet: (val: number) => void
) {
  // Financial parameters
  const [wiborPct, setWiborPct] = useState<number>(5.85);
  const [marginPct, setMarginPct] = useState<number>(2.0);
  const [pricingMarginPct, setPricingMarginPct] = useState<number>(15.0);
  const [initialDepositPct, setInitialDepositPct] = useState<number>(0);
  const [otherServiceCosts, setOtherServiceCosts] = useState<number>(0);

  // Toggles
  const [expressPaysInsurance, setExpressPaysInsurance] = useState(true);
  const [replacementCar, setReplacementCar] = useState(true);
  const [gpsRequired, setGpsRequired] = useState(true);
  const [includeServicing, setIncludeServicing] = useState(true);
  const [hookInstallation, setHookInstallation] = useState(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

  // Service cost type
  const [serviceCostType, setServiceCostType] = useState<"ASO" | "nonASO">("ASO");

  // Vehicle vintage
  const [vehicleVintage, setVehicleVintage] = useState<"current" | "previous">(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cs = (vehicle.synthesis_data as any)?.card_summary;
    if (cs?.is_current_year_vehicle === false) return "previous";
    return "current";
  });

  // Metalik
  const [isMetalic, setIsMetalic] = useState<boolean>(autoDetectMetalic());

  // Save State
  const [isSavingSetup, setIsSavingSetup] = useState(false);

  // Restore saved calculator_setup
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setup = (vehicle.synthesis_data as any)?.calculator_setup;

    if (!setup) {
      setIsMetalic(autoDetectMetalic());
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

    if (setup.financial_params) {
      const fp = setup.financial_params;
      if (fp.wibor_pct != null) setWiborPct(fp.wibor_pct);
      if (fp.margin_pct != null) setMarginPct(fp.margin_pct);
      if (fp.pricing_margin_pct != null) setPricingMarginPct(fp.pricing_margin_pct);
      if (fp.initial_deposit_pct != null) setInitialDepositPct(fp.initial_deposit_pct);
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

    if (setup.toggles) {
      const t = setup.toggles;
      if (t.express_pays_insurance != null) setExpressPaysInsurance(t.express_pays_insurance);
      if (t.replacement_car != null) setReplacementCar(t.replacement_car);
      if (t.gps_required != null) setGpsRequired(t.gps_required);
      if (t.include_servicing != null) setIncludeServicing(t.include_servicing);
      if (t.hook_installation != null) setHookInstallation(t.hook_installation);
    }

    if (setup.tire_params) {
      const tp = setup.tire_params;
      if (tp.tire_class != null) setTireClass(tp.tire_class);
      if (tp.tire_count_mode != null) setTireCountMode(tp.tire_count_mode);
      if (tp.tire_cost_correction_enabled != null) setTireCostCorrectionEnabled(tp.tire_cost_correction_enabled);
      if (tp.tire_cost_correction != null) setTireCostCorrection(tp.tire_cost_correction);
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

    if (setup.is_metalic != null) {
      const keywordDetected = autoDetectMetalic();
      const color = (vehicle.exterior_color || "").toLowerCase();
      const hasKeyword = [
        "metalic", "metalik", "metallic", "metalizow", "perłowy",
        "pearl", "mica", "xirallic", "special efekt", "dwuwarstwow"
      ].some(kw => color.includes(kw)) ||
      ["solido", "uni ", "akrylow", "jednowarstwow"].some(kw => color.includes(kw));
      
      setIsMetalic(hasKeyword ? keywordDetected : setup.is_metalic);
    } else {
      setIsMetalic(autoDetectMetalic());
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.id, vehicle.synthesis_data, vehicle.exterior_color, vehicle.wheels]);

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
  };
}
