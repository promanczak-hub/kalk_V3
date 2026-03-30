export interface FactoryOption {
  id: number;
  name: string;
  price_net: number;
  price_gross: number;
  is_non_discountable: boolean;
  is_residual_impacting: boolean;
}

export interface ServiceOption {
  id: number;
  name: string;
  price_net: number;
  price_gross: number;
  is_non_discountable: boolean;
  is_residual_impacting: boolean;
}

export interface FinancialComponent {
  value?: number;
  margin_distribution?: number;
  margin_amount?: number;
  cost_plus_margin?: number;
  margin_distribution_correction?: number;
  margin_amount_correction?: number;
  cost_plus_margin_correction?: number;
}

export interface MainMatrixParameters {
  total_interest_cost?: FinancialComponent;
  residual_value_loss?: FinancialComponent;
  duration_months?: number;
  total_insurance?: FinancialComponent;
  replacement_car_cost?: FinancialComponent;
  service_cost?: FinancialComponent;
  tires_cost?: FinancialComponent;
  additional_costs?: FinancialComponent;
  total_financial_rent?: FinancialComponent;
  total_technical_rent?: FinancialComponent;
  total_cost?: FinancialComponent;
  financial_cost?: FinancialComponent;
  technical_cost?: FinancialComponent;
  insurance_cost?: FinancialComponent;
  replacement_car_node?: FinancialComponent;
  service_node?: FinancialComponent;
  tires_node?: FinancialComponent;
  admin_cost?: FinancialComponent;
  total_cost_with_margin?: FinancialComponent;
}

export interface CalculatorInput {
  vehicle_id: string;
  calculation_number: string;
  id: string; // Changed to string for UUID compatibility
  factory_options: FactoryOption[];
  service_options: ServiceOption[];
  vat_rate: number;

  // Contract data
  margin: number;
  rent_type: string;
  rent_amount: number;
  rent_pct: number;
  initial_rent: number;
  duration_months: number;
  annual_mileage: number;
  production_year: string;
  brand: string;
  model: { id: number; type: string; dn: string } | string;
  body_type: string;
  samar_class: string;
  engine_power_hp: string;
  trim_level: string;
  fuel_type: string;
  homologation_type: string;
  residual_value_class: string;

  // Tires
  has_tires: boolean;
  tire_size: {
    width: string;
    profile: string;
    letter: string;
    diameter: string;
  };
  tire_class: string;
  tire_sets_count: string;

  // Corrections
  other_service_costs: number;
  service_package_amount: number;
  service_package_name: string | null;
  rv_correction: number;
  volume_discount_id: string | null;
  wibor_pct: number;
  financial_margin_pct: number;
  amortization_pct?: number;
  notes: string | null;
  is_private: boolean;

  // Pricing
  base_price_net: number;
  base_price_gross: number;
  is_metallic_paint: boolean;
  discount_type: string;
  discount_pct: number;
  discount_amount_net: number;
  discount_amount_gross: number;

  // Options
  has_replacement_car: boolean;
  is_insurance_included: boolean;
  is_service_included: boolean;
  has_gps: boolean;
  has_theft_insurance: boolean | null;
  is_driving_school: boolean | null;
  green_card?: boolean;
  nnw?: boolean;
  assistance?: boolean;
  insurance_cost_correction: number;
  preparation_cost_correction: number;
  tires_cost_correction: number;

  // Results
  calculation_results?: MainMatrixParameters;
}

export interface ControlCenterSettings {
  id: number;
  vat_rate: number;
  default_wibor: number;
  bank_spread: number;
  insurance_rate_pct?: number;
  provision_pct?: number;
  default_ltr_margin?: number;
}

