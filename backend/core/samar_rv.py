from typing import Optional, Dict, Any, cast
import re
from core.database import supabase

# Mapping for SAMAR class names to IDs
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


class SamarRVCalculator:
    """
    Kalkulator Utraty Wartości SAMAR (Oparta na nowych tabelach parametrycznych)
    """

    def __init__(self, vehicle_data: Dict[str, Any], calc_input: Any):
        self.vehicle = vehicle_data
        self.input = calc_input
        self.fuel_type_id = self._map_fuel_type(self.vehicle.get("Paliwo"))

        class_name = self.vehicle.get("Segment", "B")  # fallback
        self.class_id = get_samar_class_id(class_name) or 1  # default to 1 (first ID)

        self.production_year = self.vehicle.get("MinRokProd", 2024)

        # Cache class config
        self.class_config = self._fetch_class_config()

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
        return {"mileage_cutoff_threshold": 190000}  # Fallback

    def get_depreciation_rates(self, rok: int) -> Dict[str, float]:
        """Zwraca słownik deprecjacji (baza, opcje) na dany rok z samar_class_depreciation_rates"""
        try:
            res = (
                supabase.table("samar_class_depreciation_rates")
                .select("base_depreciation_percent, options_depreciation_percent")
                .eq("fuel_type_id", self.fuel_type_id)
                .eq("samar_class_id", self.class_id)
                .eq("year", rok)
                .execute()
            )
            if res.data and len(res.data) > 0:
                row_dict = cast(Dict[str, Any], res.data[0])
                return {
                    "base": float(row_dict.get("base_depreciation_percent", 0.0)),
                    "options": float(row_dict.get("options_depreciation_percent", 0.0)),
                }
        except Exception:
            pass
        # Fallback rates if not found (e.g. 50% retained at yr 0, 8% per year drop later)
        # Using heuristic from old sys
        if rok == 0:
            return {"base": 0.50, "options": 1.0}
        return {"base": 0.08, "options": 0.0}

    def get_color_correction(self) -> float:
        """Korekta za kolor analizując zasady przypisane lakierowi z paint_parsing_rules i paint_types"""
        if (
            not hasattr(self.input.settings, "samar_rv_apply_color_correction")
            or not self.input.settings.samar_rv_apply_color_correction
        ):
            return 0.0

        raw_color_string = self.vehicle.get("LakierRodzaj", "")
        if not raw_color_string:
            return 0.0

        # Odpytaj o definicje typów kolorów z bazy i dopasuj
        try:
            rules_res = supabase.table("paint_parsing_rules").select("*").execute()
            matched_paint_type_id = None
            if rules_res.data:
                for rule in rules_res.data:
                    regex = rule.get("keyword_regex", "")
                    if regex and re.search(regex, raw_color_string, re.IGNORECASE):
                        matched_paint_type_id = rule.get("paint_type_id")
                        break

            # Jak znaleźliśmy dopasowanie to wyciągnij offset
            if matched_paint_type_id:
                adj_res = (
                    supabase.table("samar_class_paint_adjustments")
                    .select("adjustment_percent")
                    .eq("samar_class_id", self.class_id)
                    .eq("paint_type_id", matched_paint_type_id)
                    .execute()
                )
                if adj_res.data and len(adj_res.data) > 0:
                    return float(adj_res.data[0].get("adjustment_percent", 0.0))
        except Exception as e:
            print(f"Error fetching paint adjustment: {e}")
            pass
        return 0.0

    def get_body_correction(self) -> float:
        """Korekta za rodzaj zabudowy (zostaje na razie stary słownik lub ew. zero, dopóki klient nie zmieni)"""
        # Możemy docelowo wyłączyć to, ale zostawię to kompatybilne.
        # Wg notatek wyłączamy markę, o zabudowie nic nie było, ale może zróbmy 0.0
        return 0.0

    def get_vintage_correction(self, rocznik: str) -> float:
        """Korekta za rocznik pojazdu"""
        # Dla uproszczenia (starszy rocznik szybciej traci), na razie 0.0, aby skupić się na SAMAR
        return 0.0

    def get_mileage_correction(self) -> Dict[str, float]:
        """Zwraca słownik korekt za przebieg"""
        ret = {"under_threshold": 0.0, "over_threshold": 0.0}
        try:
            res = (
                supabase.table("samar_class_mileage_corrections")
                .select("under_threshold_percent, over_threshold_percent")
                .eq("samar_class_id", self.class_id)
                .eq("fuel_type_id", self.fuel_type_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                row_dict = cast(Any, res.data[0])
                ret["under_threshold"] = float(
                    row_dict.get("under_threshold_percent", 0.0)
                )
                ret["over_threshold"] = float(
                    row_dict.get("over_threshold_percent", 0.0)
                )
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
        Oblicza kwotę Końcową (RV) na podstawie algorytmu SAMAR
        (z parametrycznymi progami i tabelami, np. nowy limit nadprzebiegu)
        """
        years = months // 12
        if years < 1:
            years = 1

        # 1. Pobranie bazy %
        # base_pct in year 0 is our 48 or 48WR% base equivalent (or year 0 base)
        year_0_rates = self.get_depreciation_rates(0)
        base_pct = year_0_rates["base"]

        # Wartość bazowego auta po latach (baza z roku 0 np) netto
        wr_wartosc_po_latach = base_pct * base_vehicle_capex

        # 2. Składana deprecjacja od bazy
        if years < 4:
            for rok in range(3, years - 1, -1):
                depr = self.get_depreciation_rates(rok)["base"]
                wr_wartosc_po_latach *= 1.0 + depr
        elif years > 4:
            for rok in range(5, years + 1):
                depr = self.get_depreciation_rates(rok)["base"]
                wr_wartosc_po_latach *= 1.0 - depr

        # 3. Dodanie opcji (Z tabeli Deprecjacji Doposażenia dla danego roku)
        if (
            hasattr(self.input.settings, "samar_rv_apply_options_depreciation")
            and self.input.settings.samar_rv_apply_options_depreciation
        ):
            opt_depr_pct = self.get_depreciation_rates(years)["options"]
            baza_z_opcjami = wr_wartosc_po_latach + (options_capex * opt_depr_pct)
        else:
            baza_z_opcjami = wr_wartosc_po_latach

        # 4. Korekty Specyficzne (Kolor / Zabudowa)
        laczna_cena_zakupu = base_vehicle_capex + options_capex
        kolor_wartosc = base_vehicle_capex * self.get_color_correction()
        zabudowa_wartosc = laczna_cena_zakupu * self.get_body_correction()  # 0

        # 5. Modyfikator za Przebieg wg definicji klasy bazy w DB!
        base_mileage = 140000.0
        unit_mil = 10000.0
        if hasattr(self.input.settings, "samar_rv_base_mileage"):
            base_mileage = float(self.input.settings.samar_rv_base_mileage)
        if hasattr(self.input.settings, "samar_rv_mileage_unit_km"):
            if self.input.settings.samar_rv_mileage_unit_km > 0:
                unit_mil = float(self.input.settings.samar_rv_mileage_unit_km)

        # Dynamiczny próg z konfiguracji (zamiast hardcoded 190.000)
        class_cutoff_threshold = float(
            self.class_config.get("mileage_cutoff_threshold", 190000)
        )

        przebieg_ponizej_bazy = min(total_km, class_cutoff_threshold) - base_mileage
        if przebieg_ponizej_bazy < 0:
            przebieg_ponizej_bazy = 0
        przebieg_powyzej_progu = max(total_km - class_cutoff_threshold, 0)

        mileage_dict = self.get_mileage_correction()
        korekta_przebieg_wypadkowa = (
            mileage_dict["under_threshold"]
            * baza_z_opcjami
            * (przebieg_ponizej_bazy / unit_mil)
        ) + (
            mileage_dict["over_threshold"]
            * baza_z_opcjami
            * (przebieg_powyzej_progu / unit_mil)
        )

        baza_bez_rocznika = (
            baza_z_opcjami
            + kolor_wartosc
            + zabudowa_wartosc
            - korekta_przebieg_wypadkowa
        )

        # 6. Rocznik
        rocznik_kwota = self.get_vintage_correction(str(self.production_year))
        final_rv = baza_bez_rocznika * (1.0 + rocznik_kwota)

        # Sanity Check Ograniczenia
        min_rv = laczna_cena_zakupu * 0.05
        max_rv = laczna_cena_zakupu * 0.95
        return max(min_rv, min(max_rv, final_rv))
