from typing import Optional, Dict, Any, cast
from core.database import supabase

# Mapping for SAMAR class names to IDs, fallback if needed or queried directly
SAMAR_CLASS_CACHE: Dict[str, int] = {}


def get_samar_class_id(class_name: str) -> Optional[int]:
    global SAMAR_CLASS_CACHE
    if not SAMAR_CLASS_CACHE:
        try:
            res = supabase.table("samar_klasa_wr").select("*").execute()
            if res.data:
                res_data = cast(Any, res.data)
                for row in res_data:
                    nazwa = str(row.get("nazwa", ""))
                    row_id = int(row.get("id", 0))
                    if nazwa:
                        SAMAR_CLASS_CACHE[nazwa.upper()] = row_id
        except Exception as e:
            print(f"Error fetching SAMAR classes: {e}")
            return None

    return SAMAR_CLASS_CACHE.get(class_name.upper())


class SamarRVCalculator:
    """
    Kalkulator Utraty Wartości SAMAR (Oparta o 7 tabel konfiguracyjnych)
    Zastępuje mock 50%.
    """

    def __init__(self, vehicle_data: Dict[str, Any], calc_input: Any):
        self.vehicle = vehicle_data
        self.input = calc_input
        self.fuel_type_id = self._map_fuel_type(self.vehicle.get("Paliwo"))
        self.brand_id = self.vehicle.get("MakeId", 0)  # Fallback to 0 if not present

        class_name = self.vehicle.get("Segment", "B")  # fallback
        self.class_id = get_samar_class_id(class_name) or 2  # default to B (id=2 in DB)

        self.production_year = self.vehicle.get("MinRokProd", 2024)

    def _map_fuel_type(self, fuel_str: Optional[str]) -> int:
        """Map string fuel type to int ID from legacy system. 1=Benzyna, 2=Diesel, 3=EV/Hybrid"""
        if not fuel_str:
            return 1  # default
        fuel = fuel_str.lower()
        if "diesel" in fuel:
            return 2
        elif "elektr" in fuel or "hybr" in fuel or "phev" in fuel:
            return 3
        return 1  # Benzyna default

    def get_base_rv_percentage(self) -> float:
        """Pobiera bazową korektę dla Klasy i Paliwa z ltr_admin_tabela_wr_klasas"""
        try:
            res = (
                supabase.table("ltr_admin_tabela_wr_klasas")
                .select("korekta_procent")
                .eq("rodzaj_paliwa", self.fuel_type_id)
                .eq("klasa_wr_id", self.class_id)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 0.50  # fallback

    def get_brand_correction(self) -> float:
        """Korekta za markę: ltr_admin_korekta_wr_markas"""
        try:
            res = (
                supabase.table("ltr_admin_korekta_wr_markas")
                .select("korekta_procent")
                .eq("rodzaj_paliwa", self.fuel_type_id)
                .eq("klasa_wr_id", self.class_id)
                .eq("marka_id", self.brand_id)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 0.0

    def get_depreciation_correction(self, rok: int) -> float:
        """Deprecjacja na dany ROK z ltr_admin_tabela_wr_deprecjacjas"""
        try:
            res = (
                supabase.table("ltr_admin_tabela_wr_deprecjacjas")
                .select("korekta_procent")
                .eq("rodzaj_paliwa", self.fuel_type_id)
                .eq("klasa_wr_id", self.class_id)
                .eq("rok", rok)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 0.0

    def get_options_depreciation(self, lata: int) -> float:
        """Korekta z opcji fabrycznych (doposażenia) z ltr_admin_tabela_wr_doposazenies"""
        try:
            res = (
                supabase.table("ltr_admin_tabela_wr_doposazenies")
                .select("korekta_procent")
                .eq("rodzaj_paliwa", self.fuel_type_id)
                .eq("klasa_wr_id", self.class_id)
                .eq("liczba_lat", lata)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 1.0  # domyślnie 100% zachowane jeśli nie znaleziono

    def get_color_correction(self) -> float:
        """Korekta za kolor (metalik vs niemetalik)"""
        if (
            not hasattr(self.input.settings, "samar_rv_apply_color_correction")
            or not self.input.settings.samar_rv_apply_color_correction
        ):
            return 0.0

        is_metallic = self.vehicle.get("LakierRodzaj", "").lower() == "metalik"
        kolor_str = "metalik" if is_metallic else "niemetalik"
        try:
            res = (
                supabase.table("ltr_admin_korekta_wr_kolors")
                .select("korekta_procent")
                .eq("kolor", kolor_str)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 0.0

    def get_body_correction(self) -> float:
        """Korekta za rodzaj zabudowy"""
        if (
            not hasattr(self.input.settings, "samar_rv_apply_body_correction")
            or not self.input.settings.samar_rv_apply_body_correction
        ):
            return 0.0

        zabudowa = self.vehicle.get("Zabudowa", "")
        if not zabudowa:
            return 0.0

        try:
            res = (
                supabase.table("ltr_admin_korekta_wr_zabudowas")
                .select("korekta_procent")
                .eq("rodzaj_zabudowy", zabudowa)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 0.0

    def get_vintage_correction(self, rocznik: str) -> float:
        """Korekta za rocznik pojazdu"""
        try:
            res = (
                supabase.table("ltr_admin_korekta_wr_roczniks")
                .select("korekta_procent")
                .eq("rocznik", str(rocznik))
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                val = row_dict.get("korekta_procent")
                if val is not None:
                    return float(cast(Any, val))
        except Exception:
            pass
        return 0.0

    def get_mileage_correction(self) -> Dict[str, float]:
        """Zwraca słownik korekt ujemnych/dodatnich za przebieg"""
        ret = {"under_190": 0.0, "over_190": 0.0}
        try:
            res = (
                supabase.table("ltr_admin_tabela_wr_przebiegs")
                .select("korekta_procent_ponizej_190, korekta_procent_powyzej_190")
                .eq("klasa_wr_id", self.class_id)
                .execute()
            )
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                row_dict = cast(Any, res.data[0])
                under_val = row_dict.get("korekta_procent_ponizej_190")
                over_val = row_dict.get("korekta_procent_powyzej_190")
                if under_val is not None and over_val is not None:
                    ret["under_190"] = float(cast(Any, under_val))
                    ret["over_190"] = float(cast(Any, over_val))
        except Exception:
            pass
        return ret

    def calculate_rv(
        self,
        months: int,
        total_km: int,
        base_vehicle_capex: float,
        options_capex: float,
    ) -> float:
        """
        Oblicza kwotę Końcową (RV) na podstawie kaskadowego algorytmu SAMAR.
        1. Parametry z ControlSettings
        2. Generowanie Bazy
        3. Aplikowanie poszczególnych modyfikatorów
        """
        years = months // 12
        if years < 1:
            years = 1

        # 1. Baza RV = Tabel Klasa + Tabela Marka
        base_pct = self.get_base_rv_percentage()
        brand_corr = self.get_brand_correction()
        total_base_pct = base_pct + brand_corr

        # Wartość 48 miesięcy bazowego auta netto
        wr_wartosc_po_latach = total_base_pct * base_vehicle_capex

        # 2. Składana deprecjacja od bazy
        if years < 4:
            for rok in range(3, years - 1, -1):
                depr = self.get_depreciation_correction(rok)
                wr_wartosc_po_latach *= 1.0 + depr
        elif years > 4:
            for rok in range(5, years + 1):
                depr = self.get_depreciation_correction(rok)
                wr_wartosc_po_latach *= 1.0 - depr

        # 3. Dodanie opcji (Tabela Doposażenia)
        if (
            hasattr(self.input.settings, "samar_rv_apply_options_depreciation")
            and self.input.settings.samar_rv_apply_options_depreciation
        ):
            opt_depr_pct = self.get_options_depreciation(years)
            baza_z_opcjami = wr_wartosc_po_latach + (options_capex * opt_depr_pct)
        else:
            baza_z_opcjami = wr_wartosc_po_latach

        # 4. Korekty Specyficzne (Kolor / Zabudowa)
        laczna_cena_zakupu = base_vehicle_capex + options_capex
        kolor_wartosc = base_vehicle_capex * self.get_color_correction()
        zabudowa_wartosc = laczna_cena_zakupu * self.get_body_correction()

        # 5. Modyfikator za Przebieg
        base_mileage = 140000.0
        unit_mil = 10000.0
        if hasattr(self.input.settings, "samar_rv_base_mileage"):
            base_mileage = float(self.input.settings.samar_rv_base_mileage)
        if hasattr(self.input.settings, "samar_rv_mileage_unit_km"):
            if self.input.settings.samar_rv_mileage_unit_km > 0:
                unit_mil = float(self.input.settings.samar_rv_mileage_unit_km)

        przebieg_ponizej_bazy = min(total_km, 190000) - base_mileage
        if przebieg_ponizej_bazy < 0:
            przebieg_ponizej_bazy = 0  # Wg C# Math.Min(Przebieg, 190k) - 140k
        przebieg_powyzej_190 = max(total_km - 190000, 0)

        mileage_dict = self.get_mileage_correction()
        korekta_przebieg_wypadkowa = (
            mileage_dict["under_190"]
            * baza_z_opcjami
            * (przebieg_ponizej_bazy / unit_mil)
        ) + (
            mileage_dict["over_190"]
            * baza_z_opcjami
            * (przebieg_powyzej_190 / unit_mil)
        )

        baza_bez_rocznika = (
            baza_z_opcjami
            + kolor_wartosc
            + zabudowa_wartosc
            - korekta_przebieg_wypadkowa
        )

        # 6. Finał - Korekta Rocznikowa
        rocznik_kwota = self.get_vintage_correction(str(self.production_year))
        final_rv = baza_bez_rocznika * (1.0 + rocznik_kwota)

        # Sanity Check Ograniczenia
        min_rv = laczna_cena_zakupu * 0.05
        max_rv = laczna_cena_zakupu * 0.95
        return max(min_rv, min(max_rv, final_rv))
