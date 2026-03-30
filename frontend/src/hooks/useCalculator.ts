import { useState, useEffect } from "react";
import axios from "axios";
import type { CalculatorInput, ControlCenterSettings } from "../types";
import { API_BASE_URL } from "../config/env";

export interface CalculationStep {
  krok: string;
  wynik: number;
  rownanie?: string;
  details?: Record<string, any>;
}

export interface CalculationResult {
  total_rent: number;
  steps: CalculationStep[];
  summary?: {
    base_price_net: number;
    total_discount_net: number;
    final_price_net: number;
  }
}

const INITIAL_DATA: CalculatorInput = {
  vehicle_id: "0",
  calculation_number: "NEW/2026",
  id: "temp-id",
  factory_options: [],
  service_options: [],
  vat_rate: 0.23,
  margin: 0.13,
  rent_type: "Kwotowo",
  rent_amount: 0.0,
  rent_pct: 0.0,
  initial_rent: 0.0,
  duration_months: 48,
  annual_mileage: 20000,
  production_year: "bieżący",
  brand: "",
  model: "",
  body_type: "",
  samar_class: "",
  engine_power_hp: "",
  trim_level: "",
  fuel_type: "",
  homologation_type: "",
  residual_value_class: "",
  has_tires: true,
  tire_size: { width: "225", profile: "45", letter: "R", diameter: "17" },
  tire_class: "MEDIUM",
  tire_sets_count: "Automatycznie",
  other_service_costs: 0.0,
  service_package_amount: 0.0,
  service_package_name: null,
  rv_correction: 0.0,
  volume_discount_id: null,
  wibor_pct: 0.05,
  financial_margin_pct: 0.02,
  notes: null,
  is_private: false,
  base_price_net: 0,
  base_price_gross: 0,
  is_metallic_paint: false,
  discount_type: "Procentowo",
  discount_pct: 0,
  discount_amount_net: 0,
  discount_amount_gross: 0,
  has_replacement_car: true,
  is_insurance_included: true,
  is_service_included: true,
  has_gps: true,
  has_theft_insurance: null,
  is_driving_school: null,
  insurance_cost_correction: 0.0,
  preparation_cost_correction: 0.0,
  tires_cost_correction: 0.0,
};

export function useCalculator() {
  const [data, setData] = useState<CalculatorInput>(INITIAL_DATA);
  const [isParserOpen, setIsParserOpen] = useState(false);
  const [parserText, setParserText] = useState("");
  const [isParsing, setIsParsing] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [steps, setSteps] = useState<CalculationStep[]>([]);
  const [expandedPanel, setExpandedPanel] = useState<string | false>("panel1");

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const resp = await axios.get<ControlCenterSettings>(`${API_BASE_URL}/api/control-center`);
      if (resp.data) {
        setData((prev) => ({
          ...prev,
          vat_rate: (resp.data.vat_rate ?? 23) / 100,
          wibor_pct: (resp.data.default_wibor ?? 5.0) / 100,
          financial_margin_pct: (resp.data.bank_spread ?? 2.0) / 100,
        }));
      }
    } catch (e) {
      console.error("Failed to fetch settings", e);
    }
  };

  const handleUpdate = (field: keyof CalculatorInput, value: any) => {
    setData((prev) => ({ ...prev, [field]: value }));
  };

  const handleUpdateNetto = (netto: number) => {
    setData((prev) => {
      const vat = prev.vat_rate || 0.23;
      const brutto = netto * (1 + vat);
      return {
        ...prev,
        base_price_net: netto,
        base_price_gross: brutto,
      };
    });
  };

  const handleUpdateBrutto = (brutto: number) => {
    setData((prev) => {
      const vat = prev.vat_rate || 0.23;
      const netto = brutto / (1 + vat);
      return {
        ...prev,
        base_price_net: netto,
        base_price_gross: brutto,
      };
    });
  };

  const handleChangeTypRabatu = (typ: "Procentowo" | "Kwotowo") => {
    handleUpdate("discount_type", typ);
  };

  const handleUpdateRabat = (typ: string, value: number) => {
    if (typ === "Procentowo") {
      handleUpdate("discount_pct", value / 100);
    } else {
      handleUpdate("discount_amount_net", value);
    }
  };

  const addFactoryOption = () => {
    const nextId = Date.now();
    setData(prev => ({
      ...prev,
      factory_options: [...prev.factory_options, {
        id: nextId,
        name: "Nowa opcja fabryczna",
        price_net: 0,
        price_gross: 0,
        is_non_discountable: false,
        is_residual_impacting: false
      }]
    }));
  };

  const removeFactoryOption = (id: number) => {
    setData(prev => ({
      ...prev,
      factory_options: prev.factory_options.filter(o => o.id !== id)
    }));
  };

  const addServiceOption = () => {
    const nextId = Date.now();
    setData(prev => ({
      ...prev,
      service_options: [...prev.service_options, {
        id: nextId,
        name: "Nowa opcja serwisowa",
        price_net: 0,
        price_gross: 0,
        is_non_discountable: false,
        is_residual_impacting: false
      }]
    }));
  };

  const removeServiceOption = (id: number) => {
    setData(prev => ({
      ...prev,
      service_options: prev.service_options.filter(o => o.id !== id)
    }));
  };

  const calculate = async () => {
    setIsCalculating(true);
    try {
      const payload = {
        ...data,
        base_price_net: data.base_price_net || 0,
        okres_bazowy: data.duration_months,
        przebieg_bazowy: data.duration_months * (data.annual_mileage / 12 * 12), // normalize to contract total if needed
        samar_category: data.samar_class,
        engine_name: data.fuel_type,
        body_type_name: data.body_type,
        power_hp: Number(data.engine_power_hp) || 0,
      };

      const response = await axios.post(`${API_BASE_URL}/api/ltr/calculate-manual`, payload);
      if (response.data) {
        setCalculationResult({
          total_rent: response.data.total_rent || 0,
          steps: response.data.steps || [],
          summary: response.data.summary
        });
        setSteps(response.data.steps || []);
      }
    } catch (err) {
      console.error("Calculation failed", err);
    } finally {
      setIsCalculating(false);
    }
  };

  const updateVehicle = (updates: Partial<CalculatorInput>) => {
    setData(prev => ({ ...prev, ...updates }));
  };

  const [activeStep, setActiveStep] = useState(0);

  const handleNext = () => setActiveStep((prev) => prev + 1);
  const handleBack = () => setActiveStep((prev) => prev - 1);
  const handleReset = () => {
    setData(INITIAL_DATA);
    setActiveStep(0);
    setCalculationResult(null);
    setSteps([]);
  };

  const handleAccordionChange = (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPanel(isExpanded ? panel : false);
  };

  return {
    vehicle: data,
    updateVehicle,
    factoryOptions: data.factory_options,
    serviceOptions: data.service_options,
    handleUpdate,
    handleUpdateNetto,
    handleUpdateBrutto,
    handleUpdateRabat,
    handleChangeTypRabatu,
    addFactoryOption,
    removeFactoryOption,
    addServiceOption,
    removeServiceOption,
    calculationResult,
    steps,
    isCalculating,
    calculate,
    isParserOpen,
    setIsParserOpen,
    parserText,
    setParserText,
    isParsing,
    expandedPanel,
    handleAccordionChange,
    activeStep,
    handleNext,
    handleBack,
    handleReset,
  };
}
