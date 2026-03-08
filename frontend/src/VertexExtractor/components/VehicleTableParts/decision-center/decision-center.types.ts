// ── Decision Center — Shared Types ────────────────────────────────────────────

export interface CostComponent {
  base: number;
  margin: number;
  price: number;
  rozklad_marzy?: number;
}

export interface CellBreakdown {
  finance: CostComponent & {
    monthly_pmt_z_czynszem?: number;
    monthly_pmt_bez_czynszu?: number;
    suma_odsetek_z_czynszem?: number;
    suma_odsetek_bez_czynszu?: number;
    czynsz_inicjalny_netto?: number;
    wykup_kwota?: number;
  };
  technical: {
    service: CostComponent;
    tires: CostComponent & { ilosc_opon?: number };
    insurance: CostComponent;
    replacement_car: CostComponent;
    additional_costs: CostComponent;
  };
}

export interface MiniMatrixCell {
  months: number;
  km_per_year: number;
  total_km: number;
  price_net: number;
  base_cost_net: number;
  marza_mc: number;
  marza_na_kontrakcie: number;
  marza_na_kontrakcie_pct: number;
  czynsz_finansowy: number;
  czynsz_techniczny: number;
  rv_samar_net: number;
  koszt_dzienny: number;
  koszty_ogolem: number;
  breakdown: CellBreakdown;
  status: string;
}

export interface MarginTier {
  label: string;
  heatColor: string;
  heatBg: string;
  textColor: string;
  borderColor: string;
  badgeBg: string;
  badgeText: string;
}

export type SortCriterion = "price" | "margin_pct" | "margin_value" | "ratio";
