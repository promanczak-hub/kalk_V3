export interface PricingComponent {
  label: string;
  amount_net: number;
  no_discount: boolean;
}

export interface PricingState {
  components: PricingComponent[];
  discount_pct: number;
}

export interface PricingResult {
  components: PricingComponent[];
  discount_pct: number;
  discountable_sum: number;
  non_discountable_sum: number;
  total_sum_net: number;
  discount_amount: number;
  purchase_price_net: number;
  vat_amount: number;
  purchase_price_gross: number;
}

export interface KalkulacjaListItem {
  id: string;
  numer_kalkulacji: string;
  status: string;
  source?: 'pdf' | 'manual' | 'clone';
  dane_pojazdu?: string;
  cena_netto?: number;
  created_at: string;
  updated_at: string;
  body_type?: string;
  fuel_type?: string;
  discount_pct?: number;
  options_count?: number;
}

export interface KalkulacjaDetail extends KalkulacjaListItem {
  stan_json?: Record<string, unknown>;
}

export const DEFAULT_PRICING_COMPONENTS: PricingComponent[] = [
  { label: 'Cena katalogowa netto', amount_net: 0, no_discount: false },
  { label: 'Transport netto', amount_net: 0, no_discount: true },
  { label: 'Opony netto', amount_net: 0, no_discount: false },
  { label: 'Abonament GSM netto', amount_net: 0, no_discount: false },
  { label: 'Inne składowe netto', amount_net: 0, no_discount: false },
];
