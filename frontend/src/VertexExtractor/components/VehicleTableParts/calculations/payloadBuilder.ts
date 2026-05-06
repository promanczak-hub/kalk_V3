import type { FleetVehicleView } from "../../../types";
import { extractOptionsFromPaidOptions } from "./calculations.utils";

export interface CalculationPayloadParams {
    vehicle: FleetVehicleView;
    wiborPct: number | null; // Nulled by default to use DB ControlCenter
    marginPct: number | null; 
    pricingMarginPct: number;
    initialDepositPct: number;
    otherServiceCosts: number | null; 
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
    priceAudit?: {
      threshold_pln: number;
      ai_base_price_netto: number;
      final_base_price_netto: number;
      delta_pln: number;
      manual_review_required: boolean;
    };
}

export function buildCalculationPayload(params: CalculationPayloadParams): Record<string, unknown> {
    const { vehicle, priceAudit } = params;
    
    // Extract base state
    const existingCalculatorSetup = ((vehicle.synthesis_data as Record<string, unknown>)?.calculator_setup as Record<string, unknown>) || {};
    const existingFinancialParams = (existingCalculatorSetup.financial_params as Record<string, unknown>) || {};
    const existingToggles = (existingCalculatorSetup.toggles as Record<string, unknown>) || {};
    
    // Extract baseline pricing safely
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sd = (vehicle.synthesis_data as Record<string, any>) || {};
    const cs = sd.card_summary || {};
    const setup = sd.calculator_setup || {};
    const pp = cs.parsed_prices || {};
    const uf = sd.universal_features || {};
    const comp = sd.computed || {};

    const isDemo = String(cs.is_demo || "").toLowerCase() === "true";
    
    // Robust hierarchy for price discovery
    const rawBasePrice = setup.catalog_base_price_net || 
      (isDemo ? (cs.demo_price || cs.base_price) : cs.base_price) || 
      cs.total_price || 
      pp.base || 
      uf.cena_pojazdu || 
      comp.estimated_price || 
      "0";
      
    // Remove whitespaces and format to float
    const cleanBasePrice = typeof rawBasePrice === "number" ? rawBasePrice : parseFloat(String(rawBasePrice || "").replace(/\s+/g, "").replace(",", ".")) || 0;
    const priceDomain = cs._price_domain || cs.price_domain || "unknown";
    const isBrutto = String(rawBasePrice || "").toLowerCase().includes("brutto") || priceDomain === "brutto";
    
    // Normalize to Net
    const basePriceNet = isBrutto ? parseFloat((cleanBasePrice / 1.23).toFixed(2)) : cleanBasePrice;

    // Convert options array using business logic
    const fallbackFromPaid = extractOptionsFromPaidOptions(
      cs.paid_options || [],
      String(cs._price_domain || cs.price_domain || "")
    );

    // Calculate rim diameter
    const finalRimDiameter = params.rimDiameter || 
      (cs.wheels ? parseInt(String(cs.wheels).replace(/\D/g, "")) : 16) || 16;
      
    const tireCount = params.tireCountMode === "auto" ? null : 
      (isNaN(parseFloat(params.tireCountMode)) ? null : parseFloat(params.tireCountMode));

    // Compile payload
    return {
        ...(vehicle.synthesis_data || {}),
        vehicle_id: vehicle.id,
        base_price_net: basePriceNet,
        factory_options: fallbackFromPaid.factory,
        service_options: fallbackFromPaid.service,
        brand: vehicle.brand || "",
        model: vehicle.model || "",
        
        // Critical Fix: Explicitly pass transmission to backend
        gearbox_name: vehicle.transmission || cs.transmission || uf.skrzynia_biegow || comp.transmission || "",
        drive_type: vehicle.drive_type || cs.drive_type || "",
        
        // Ensure critical fields match backend validation explicitly
        power_kw: Number(sd.power_kw ?? cs.power_kw ?? (cs.power_hp ? Number(cs.power_hp) * 0.73549875 : 0)),
        paint_type_name: sd.mapped_ai_data?.color ?? sd.typ_lakieru ?? sd.paint_type_name ?? cs.color ?? "",
        body_type_name: sd.mapped_ai_data?.body_type ?? sd.body_type_name ?? cs.body_style ?? cs.body_type ?? "",
        zabudowa_type_id: sd.zabudowa_type_id ?? ((typeof cs.zabudowa_type_id === "number") ? cs.zabudowa_type_id : null),
        samar_category: sd.mapped_ai_data?.samar_category ?? sd.samar_category ?? cs.samar_category ?? "",
        engine_name: sd.mapped_ai_data?.fuel ?? sd.engine_category ?? cs.engine_category ?? cs.powertrain ?? cs.fuel_type ?? uf.rodzaj_paliwa ?? "",

        // Flattened fields strictly required by backend's CalculatorInput model cache job
        // Note: we leave wibor_pct and margin_pct passing what we have, but we will pass null 
        // if UI defaults to not overriding (or change UI to send null contextually)
        // Here we just map what the builder is given
        wibor_pct: params.wiborPct,
        margin_pct: params.marginPct,
        pricing_margin_pct: params.pricingMarginPct,
        discount_pct: params.activeDiscountPct,
        depreciation_pct: null,
        initial_deposit_pct: params.initialDepositPct,
        inne_koszty_serwisowania_netto: params.otherServiceCosts,
        
        replacement_car_enabled: params.replacementCar,
        add_gsm_subscription: params.gpsRequired,
        add_hook_installation: params.hookInstallation,
        include_servicing: params.includeServicing,
        
        z_oponami: params.includeTires,
        klasa_opony_string: params.tireClass || "Medium",
        liczba_kompletow_opon: tireCount,
        korekta_kosztu_opon: params.tireCostCorrectionEnabled,
        koszt_opon_korekta: params.tireCostCorrectionMap,
        srednica_felgi: finalRimDiameter,
        
        financial_params: {
          ...existingFinancialParams,
          wibor_pct: params.wiborPct,
          margin_pct: params.marginPct,
          pricing_margin_pct: params.pricingMarginPct,
          depreciation_pct: null,
          initial_deposit_pct: params.initialDepositPct,
          other_service_costs: params.otherServiceCosts,
        },
        toggles: {
          ...existingToggles,
          express_pays_insurance: params.expressPaysInsurance,
          replacement_car: params.replacementCar,
          gps_required: params.gpsRequired,
          include_servicing: params.includeServicing,
          include_tires: params.includeTires,
          hook_installation: params.hookInstallation,
        },
        tire_params: {
          tire_class: params.tireClass,
          tire_count_mode: params.tireCountMode,
          tire_cost_correction_enabled: params.tireCostCorrectionEnabled,
          tire_cost_correction_map: params.tireCostCorrectionMap,
          rim_diameter: params.rimDiameter,
        },
        service_cost_type: params.serviceCostType,
        vehicle_vintage: params.vehicleVintage,
        paint_category_id: params.paintCategoryId,
        paint_type_id: params.paintCategoryId ?? null,
        discount: {
          active_discount_pct: params.activeDiscountPct,
          active_final_price: params.activeFinalPrice,
        },
        pricing_governance: {
          ai_as_suggestion_only: true,
          manual_review_required: priceAudit?.manual_review_required ?? false,
          ai_price_alert_threshold_pln: priceAudit?.threshold_pln ?? null,
          ai_base_price_netto: priceAudit?.ai_base_price_netto ?? null,
          final_base_price_netto: priceAudit?.final_base_price_netto ?? null,
          delta_pln: priceAudit?.delta_pln ?? null,
          reviewed_at: new Date().toISOString(),
        },
      };
}
