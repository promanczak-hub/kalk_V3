export interface ParametryGlobalne {
  stawka_vat: number;
  czas_przygotowania_do_sprzedazy: number;
  przewidywana_cena_sprzedazy_lo: number;
  korekta_serwis_procent: number;
  domyslna_marza_finansowa: number;
  marza_handlowa: number;
  domyslny_wibor: number;
  koszty_dodatkowe_stale: number;
  stawka_serwisowa_za_km: number | null;
  domyslna_cena_gps: number;
  domyslna_stawka_zastepczy: number;
  wibor?: number;
  marza_finansowa?: number;
  koszt_przekladki_opon_netto?: number;
  przygotowanie_do_sprzedazy_netto?: number;
}

export const DOMYSLNE_PARAMETRY: ParametryGlobalne = {
  stawka_vat: 1.23,
  czas_przygotowania_do_sprzedazy: 2,
  przewidywana_cena_sprzedazy_lo: 15,
  korekta_serwis_procent: 0,
  domyslna_marza_finansowa: 5,
  marza_handlowa: 0.1, // 10%
  domyslny_wibor: 5.85,
  koszty_dodatkowe_stale: 1500,
  stawka_serwisowa_za_km: null, // Jeśli null, używa tabel
  domyslna_cena_gps: 1200,
  domyslna_stawka_zastepczy: 100,
};
