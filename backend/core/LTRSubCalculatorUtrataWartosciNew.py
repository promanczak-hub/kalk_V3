from typing import Optional, Dict, Any, cast
from core.database import supabase

SAMAR_CLASS_CACHE: Dict[str, int] = {}


def get_samar_class_id(class_name: str) -> Optional[int]:
    global SAMAR_CLASS_CACHE
    if not SAMAR_CLASS_CACHE:
        try:
            res = supabase.table("samar_classes").select("id, name").execute()
            if res.data:
                res_data = cast(Any, res.data)
                for row in res_data:
                    nazwa = str(row.get("name", ""))
                    row_id = int(row.get("id", 0))
                    if nazwa:
                        SAMAR_CLASS_CACHE[nazwa.upper()] = row_id
        except Exception as e:
            print(f"Error fetching SAMAR classes: {e}")
            return None

    return SAMAR_CLASS_CACHE.get(class_name.upper())


class LTRSubCalculatorUtrataWartosciNew:
    """
    Nowy wariant Kalkulatora Utraty Wartości SAMAR zastępujący starą logikę.
    Odpowiada za wyliczenie: WR (Końcowe), WRdlaLO oraz UtrataWartosciBEZczynszu.
    Kalkulator operuje niemal do samego końca na wartościach brutto.
    """

    def __init__(self, vehicle_data: Dict[str, Any], calc_input: Any):
        self.vehicle = vehicle_data
        self.input = calc_input
        self.fuel_type_id = self._map_fuel_type(self.vehicle.get("Paliwo"))

        class_name = self.vehicle.get("Segment", "B")  # fallback
        self.class_id = get_samar_class_id(class_name) or 1  # default to 1

        self.production_year = self.vehicle.get("MinRokProd", 2024)
        self.class_config = self._fetch_class_config()

        # Pobierz parametry z bazy
        self.vat_rate = self._fetch_global_param("VAT", fallback=1.23)
        self.przewidywana_cena_lo = self._fetch_global_param(
            "PrzewidywanaCenaSprzedazyLO", fallback=0.0
        )

        # Fix dla VAT rate jeśli jest wprocentach wpisane
        if self.vat_rate > 1.0 and self.vat_rate < 2.0:
            pass
        elif self.vat_rate >= 20.0:
            self.vat_rate = 1.0 + (self.vat_rate / 100.0)
        else:
            self.vat_rate = 1.23

    def _fetch_global_param(self, param_name: str, fallback: float) -> float:
        """Pobiera parametry globalne z tabeli parametrów"""
        try:
            response = (
                supabase.table("LTRAdminParametry_czak")
                .select("col_2")
                .ilike("col_1", param_name)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                row = cast(Dict[str, Any], response.data[0])
                val = row.get("col_2")
                if val is not None:
                    return float(str(val).replace(",", "."))
        except Exception:
            pass
        return fallback

    def _map_fuel_type(self, fuel_str: Optional[str]) -> int:
        """Mapuje nazwę napędu na fuel_group_id (1=Benzyna, 2=Diesel, 3=Alternatywne).

        Odpytuje tabelę engines po nazwie. Fallback: heurystyka substring.
        """
        if not fuel_str:
            return 1
        try:
            res = (
                supabase.table("engines")
                .select("fuel_group_id")
                .eq("name", fuel_str)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return int(res.data[0].get("fuel_group_id", 1))
        except Exception:
            pass
        # Fallback heuristic for legacy/unmapped values
        fuel = fuel_str.lower()
        if "diesel" in fuel or "(on)" in fuel:
            return 2
        if any(
            kw in fuel
            for kw in ("elektr", "hybr", "phev", "hev", "bev", "fcev", "lpg", "wodór")
        ):
            return 3
        return 1

    def _fetch_class_config(self) -> Dict[str, Any]:
        """Pobiera parametry konfiguracyjne dla Klasy SAMAR"""
        try:
            res = (
                supabase.table("samar_classes")
                .select("*")
                .eq("id", self.class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])
        except Exception:
            pass
        return {"mileage_cutoff_threshold": 190000}

    def get_base_rv_48(self) -> float:
        try:
            res = (
                supabase.table("samar_base_rv")
                .select("base_rv_percent")
                .eq("samar_class_id", self.class_id)
                .order("months", desc=True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return float(res.data[0].get("base_rv_percent", 0.0))
        except Exception:
            pass
        return 0.50

    def get_brand_correction(self) -> float:
        brand = self.vehicle.get("Marka", "")
        if not brand:
            return 0.0
        segment = self.vehicle.get("Segment", "")
        try:
            query = (
                supabase.table("samar_brand_corrections")
                .select("correction_percent")
                .ilike("marka", brand)
            )
            if segment:
                query = query.eq("klasa_samar", segment)
            res = query.limit(1).execute()
            if res.data and len(res.data) > 0:
                return float(res.data[0].get("correction_percent", 0.0))
        except Exception:
            pass
        return 0.0

    def get_vintage_depreciation(self, year: int) -> float:
        try:
            res = (
                supabase.table("samar_vintage_depreciation")
                .select("correction_percent")
                .eq("samar_class_id", self.class_id)
                .eq("year", year)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return float(res.data[0].get("correction_percent", 0.0))
        except Exception:
            pass
        return 0.08

    def get_options_depreciation_percent(self) -> float:
        try:
            res = (
                supabase.table("samar_options_depreciation")
                .select("options_depreciation_percent")
                .eq("samar_class_id", self.class_id)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return float(res.data[0].get("options_depreciation_percent", 0.0))
        except Exception:
            pass
        return 1.0

    def get_color_correction(self) -> float:
        # Samochody Dostawcze wg SAMAR (klasa_id powiązana z segmentem VAN/Dostawcze)
        # Tabela mapuje np. LCV1... W tym mocku wykorzystamy sprawdzenie "Typ Nadwozia" / "Kategoria"
        segment = str(self.vehicle.get("Segment", "")).upper()
        if "DOSTAWCZ" in segment or "VAN" in segment or "LCV" in segment:
            return 0.0

        if (
            not hasattr(self.input.settings, "samar_rv_apply_color_correction")
            or not self.input.settings.samar_rv_apply_color_correction
        ):
            return 0.0

        raw_color_string = self.vehicle.get("LakierRodzaj", "")
        if not raw_color_string:
            return 0.0

        is_metalik = False
        if "metal" in raw_color_string.lower() or "perl" in raw_color_string.lower():
            is_metalik = True

        try:
            adj_res = (
                supabase.table("samar_color_depreciation")
                .select("correction_percent")
                .eq("samar_class_id", self.class_id)
                .eq("is_metallic", is_metalik)
                .limit(1)
                .execute()
            )
            if adj_res.data and len(adj_res.data) > 0:
                adj_row = cast(Dict[str, Any], adj_res.data[0])
                return float(adj_row.get("correction_percent", 0.0))
        except Exception:
            pass
        return 0.0

    def get_body_correction(self) -> float:
        try:
            adj_res = (
                supabase.table("samar_body_depreciation")
                .select("correction_percent")
                .eq("samar_class_id", self.class_id)
                .limit(1)
                .execute()
            )
            if adj_res.data and len(adj_res.data) > 0:
                adj_row = cast(Dict[str, Any], adj_res.data[0])
                return float(adj_row.get("correction_percent", 0.0))
        except Exception:
            pass
        return 0.0

    def get_vintage_correction(self, rocznik: str) -> float:
        return 0.0

    def get_mileage_correction(self) -> Dict[str, float]:
        ret = {
            "lower_threshold_km": 140000.0,
            "upper_threshold_km": 190000.0,
            "penalty_below_upper_percent": 0.0,
            "penalty_above_upper_percent": 0.0,
            "step_km": 10000.0,
        }
        try:
            res = (
                supabase.table("samar_mileage_thresholds")
                .select("*")
                .eq("samar_class_id", self.class_id)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                ret["lower_threshold_km"] = float(
                    row_dict.get("lower_threshold_km", 140000.0)
                )
                ret["upper_threshold_km"] = float(
                    row_dict.get("upper_threshold_km", 190000.0)
                )
                ret["penalty_below_upper_percent"] = float(
                    row_dict.get("penalty_below_upper_percent", 0.0)
                )
                ret["penalty_above_upper_percent"] = float(
                    row_dict.get("penalty_above_upper_percent", 0.0)
                )
                ret["step_km"] = float(row_dict.get("step_km", 10000.0))
        except Exception:
            pass
        return ret

    def _calculate_wr_gross(
        self,
        months: int,
        total_km: int,
        base_vehicle_capex_gross: float,
        options_capex_gross: float,
    ) -> float:
        years = months // 12
        if years < 1:
            years = 1

        # Faza 1: Baza WR + Rocznik + Opcje (OkresPlusDoposazenie)
        procent_48 = self.get_base_rv_48() + self.get_brand_correction()
        wr_wartosc_po_latach = base_vehicle_capex_gross * procent_48

        if years < 4:
            for rok in range(3, years - 1, -1):
                depr = self.get_vintage_depreciation(rok)
                wr_wartosc_po_latach *= 1.0 + depr
        elif years > 4:
            for rok in range(5, years + 1):
                depr = self.get_vintage_depreciation(rok)
                wr_wartosc_po_latach *= 1.0 - depr

        if (
            hasattr(self.input.settings, "samar_rv_apply_options_depreciation")
            and self.input.settings.samar_rv_apply_options_depreciation
        ):
            opt_depr_pct = self.get_options_depreciation_percent()
            baza_z_opcjami = wr_wartosc_po_latach + (options_capex_gross * opt_depr_pct)
        else:
            baza_z_opcjami = wr_wartosc_po_latach

        laczna_cena_zakupu = base_vehicle_capex_gross + options_capex_gross
        kolor_wartosc = base_vehicle_capex_gross * self.get_color_correction()
        zabudowa_wartosc = laczna_cena_zakupu * self.get_body_correction()

        mileage_dict = self.get_mileage_correction()
        lower_threshold = mileage_dict["lower_threshold_km"]
        upper_threshold = mileage_dict["upper_threshold_km"]
        penalty_below = mileage_dict["penalty_below_upper_percent"]
        penalty_above = mileage_dict["penalty_above_upper_percent"]
        step_km = mileage_dict["step_km"]

        # Faza 2: Korekta za przebieg (Kroki kar za nadmiarowy przebieg)
        przebieg_max_ponizej = max(0, min(total_km, upper_threshold) - lower_threshold)
        kara_etap_1 = (przebieg_max_ponizej / step_km) * (
            penalty_below * baza_z_opcjami
        )

        przebieg_max_powyzej = max(0, total_km - upper_threshold)
        kara_etap_2 = (przebieg_max_powyzej / step_km) * (
            penalty_above * baza_z_opcjami
        )

        korekta_przebieg_wypadkowa = kara_etap_1 + kara_etap_2

        # Faza 3: Ujednolicenie Wartości WR
        baza_bez_rocznika = (
            baza_z_opcjami
            + kolor_wartosc
            + zabudowa_wartosc
            - korekta_przebieg_wypadkowa
        )

        # Faza 4: Korekta Ręczna WR
        korekta_reczna_wr = 0.0
        if hasattr(self.input, "manual_wr_correction"):
            korekta_reczna_wr = float(getattr(self.input, "manual_wr_correction", 0.0))
        elif isinstance(self.input, dict) and "manual_wr_correction" in self.input:
            korekta_reczna_wr = float(self.input.get("manual_wr_correction", 0.0))

        final_rv = baza_bez_rocznika + (korekta_reczna_wr * self.vat_rate)

        min_rv = laczna_cena_zakupu * 0.05
        max_rv = laczna_cena_zakupu * 0.95
        return max(min_rv, min(max_rv, final_rv))

    def calculate_values(
        self,
        months: int,
        total_km: int,
        base_vehicle_capex_gross: float,
        options_capex_gross: float,
    ) -> Dict[str, float]:
        """Zwraca slownik z WRNetto, WRdlaLO (Netto) oraz UtrataWartosciBEZczynszu (Netto)"""

        # 1. Liczymy WR Brutto z rdzenia kalkulatora
        wr_brutto_korekty = self._calculate_wr_gross(
            months, total_km, base_vehicle_capex_gross, options_capex_gross
        )

        # Ostateczne WRNetto
        wr_net = wr_brutto_korekty / self.vat_rate

        # 2. WRdlaLO
        wr_lo_brutto = wr_brutto_korekty * (1.0 + self.przewidywana_cena_lo)
        wr_lo_net = wr_lo_brutto / self.vat_rate

        # 3. UtrataWartosciBEZczynszu (Cena Zakupu Brutto - WR Brutto, zabezpieczone Math.Max)
        laczna_cena_zakupu_brutto_po_rabacie = (
            base_vehicle_capex_gross + options_capex_gross
        )
        utrata_wartosci_bez_czynszu_brutto = max(
            laczna_cena_zakupu_brutto_po_rabacie - wr_brutto_korekty, 0.0
        )

        utrata_wartosci_bez_czynszu_net = (
            utrata_wartosci_bez_czynszu_brutto / self.vat_rate
        )

        return {
            "WR_Gross": float(wr_brutto_korekty),  # Do celów debug
            "WR": float(wr_net),
            "WRdlaLO": float(wr_lo_net),
            "UtrataWartosciBEZczynszu": float(utrata_wartosci_bez_czynszu_net),
        }
