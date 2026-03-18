// ── Decision Center — Shared Types ────────────────────────────────────────────

export interface MiniMatrixCell {
  Okres: number;
  Przebieg: number;
  PrzebiegKontrakt?: number;
  LacznaStawka: number;
  CzynszFinansowy: number;
  CzynszTechniczny: number;
  Ubezpieczenie: number;
  Serwis: number;
  Admin: number;
  Opony: number;
  SamochodZastepczy: number;
  Przychod: number;
  PodstawaMarzy: number;
  MarzaMiesiac: number;
  MarzaNaKontrakcie: number;
  MarzaNaKontrakcieProcent: number;
  KosztyLaczneMC: number;
  KosztFinansowyLacznie: number;
  KosztFinansowyMiesiecznie: number;
  CenaZakupu: number;
  CenaZakupuBezOpon: number;
  CenaZakupuBezOponIOpcjiSerwisowych: number;
  CenaZakupuBezOponIOpcjiSerwisowychIPakietu: number;
  GsmCapexNetto: number;
  OpcjeSerwisoweSumaNetto: number;
  CenaKatalogowaNetto: number;
  RabatKwotowo: number;
  WR: number;
  WRdlaLO: number;
  UtrataWartosci: number;
  KorektaZaPrzebiegKwotowo: number;
  KorektaAdministracyjnaKwotowo: number;
  CzynszInicjalnyProcent: number;
  CzynszInicjalnyNetto: number;
  LacznyKosztCzesciOdsetkowejRaty: number;
  SumaOdsetekBezCzynszuInicjalnego: number;
  LacznyKosztOpon: number;
  IloscOpon: number;
  Cena1KompletOpon: number;
  Koszt1KplOpon: number;
  LacznieKosztySerwisowe: number;
  KosztySerwisowe: number;
  LacznieUbezpieczenie: number;
  KosztyDodatkowe: number;
  LacznieSamochodZastepczy: number;
  KosztyOgolem: number;
  KosztDzienny: number;
  AmortyzacjaProcent: number;
  KorektaWRMaks: number;
  ReportHtml: string;
  status: string;
  warnings?: {
    service_fallback_used?: boolean;
    replacement_car_missing?: boolean;
  };
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
