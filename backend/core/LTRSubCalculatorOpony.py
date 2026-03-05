from typing import Dict, Any, Optional, cast
import math
from core.database import supabase


class LTRSubCalculatorOpony:
    """Moduł odpowiedzialny za kalkulację kosztów opon zgodnie z V1 (LTRSubCalculatorOpony.cs)."""

    def __init__(
        self,
        z_oponami: bool,
        klasa_opony_string: str,
        srednica_felgi: int,
        korekta_kosztu: bool = False,
        koszt_opon_korekta: float = 0.0,
        sets_needed_override: Optional[int] = None,
    ):
        self.z_oponami = z_oponami
        self.srednica_felgi = srednica_felgi
        self.korekta_kosztu = korekta_kosztu
        self.koszt_opon_korekta = koszt_opon_korekta
        self.sets_needed_override = sets_needed_override

        # Mapowanie klasy opon na kolumnę DB:
        # Frontend dropdown value (np. "Wielosezon Wzmocnione Budget")
        # → kolumna DB: wielosezon_wzmocnione_budget
        klasa_lower = (
            klasa_opony_string.strip().lower() if klasa_opony_string else "medium"
        )
        self.tire_column_name = klasa_lower.replace(" ", "_")
        self.all_season = "wielosezon" in klasa_lower

        # Only fetch database data if module is active
        if self.z_oponami:
            if not self.srednica_felgi:
                raise ValueError("srednica_felgi jest wymagana gdy z_oponami=True")
            # Fetch global parameters from LTRAdminParametry_czak
            self.storage_cost_per_year = self._fetch_global_param(
                "OponyPrzechowywane", fallback=216.0
            )
            self.swap_cost = self._fetch_global_param("OponyPrzekladki", fallback=120.0)
            self.vat_rate = self._fetch_global_param("VAT", fallback=1.23)

            # Use 1.23 as fallback multiplier if DB returns flat percent like 23
            if self.vat_rate > 1.0 and self.vat_rate < 2.0:
                pass  # Example: 1.23
            elif self.vat_rate >= 20.0:
                self.vat_rate = 1.0 + (self.vat_rate / 100.0)
            else:
                self.vat_rate = 1.23

            # Configurations
            self.thresholds = self._fetch_tire_configurations()

            # Hardware cost base from DB (price per set / komplet)
            self.tire_set_price_base = self._fetch_tire_cost()

            # Adjust price if manual correction is enabled (Gross -> Net)
            if self.korekta_kosztu:
                self.tire_set_price = self.tire_set_price_base + (
                    self.koszt_opon_korekta / self.vat_rate
                )
            else:
                self.tire_set_price = self.tire_set_price_base

    def _fetch_global_param(self, param_name: str, fallback: float) -> float:
        """Pobiera parametry globalne (np. koszt przekładki/przechowywania) z bazy."""
        try:
            response = (
                supabase.table("LTRAdminParametry_czak")
                .select("col_2")
                .ilike("col_1", param_name)  # ilike for case insensitivity (VAT vs vat)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                row = cast(Dict[str, Any], response.data[0])
                val = row.get("col_2")
                if val is not None:
                    # In DB these seem to be strings like '120' or '216'
                    return float(str(val).replace(",", "."))
        except Exception as e:
            print(f"Error fetching param {param_name}: {e}")
        return fallback

    def _fetch_tire_configurations(self) -> Dict[str, float]:
        """Pobiera i mapuje progi z tabeli tyre_configurations"""
        defaults: Dict[str, float] = {
            "all_season_threshold_1": 60000.0,
            "all_season_threshold_2": 120000.0,
            "all_season_threshold_3": 180000.0,
            "all_season_threshold_4": 240000.0,
            "all_season_threshold_5": 300000.0,
            "season_threshold_1": 120000.0,
            "season_threshold_2": 180000.0,
            "season_threshold_3": 240000.0,
            "season_threshold_4": 300000.0,
        }
        try:
            res = (
                supabase.table("tyre_configurations")
                .select("config_key, config_value")
                .execute()
            )
            if res.data:
                for item in res.data:
                    row = cast(Dict[str, Any], item)
                    defaults[str(row["config_key"])] = float(row["config_value"])
        except Exception as e:
            print(f"Error fetching tyre_configurations: {e}")

        return defaults

    def _get_tire_column_name(self) -> str:
        """Zwraca nazwę kolumny w tabeli koszty_opon.

        Mapowanie 1:1 z dropdown'u frontendowego:
        'Wielosezon Wzmocnione Budget' → 'wielosezon_wzmocnione_budget'
        """
        return self.tire_column_name

    def _fetch_tire_cost(self) -> float:
        """Pobiera cenę kompletu opon (4 szt.) danej średnicy i klasy."""
        if not self.srednica_felgi:
            raise ValueError("srednica_felgi jest wymagana do pobrania ceny opon")

        column_name = self._get_tire_column_name()
        try:
            response = (
                supabase.table("koszty_opon")
                .select(column_name)
                .eq("srednica", self.srednica_felgi)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                row = cast(Dict[str, Any], response.data[0])
                val = row.get(column_name)
                if val:
                    return float(val)
        except Exception as e:
            print(
                f"Error fetching tire cost for size {self.srednica_felgi} {column_name}: {e}"
            )

        raise ValueError(
            f"Brak ceny opon w tabeli koszty_opon "
            f"dla srednica={self.srednica_felgi}, klasa={column_name}. "
            f"Uzupełnij dane w Supabase."
        )

    def _get_sets_needed(self, total_km: int) -> float:
        """Schodkowa logika ilości kompletów pobrana z tablic parametrycznych V3."""
        if self.sets_needed_override is not None:
            return float(self.sets_needed_override)

        t = self.thresholds
        if self.all_season:
            if total_km <= t.get("all_season_threshold_1", 60000):
                return 1.0
            elif total_km <= t.get("all_season_threshold_2", 120000):
                return 2.0
            elif total_km <= t.get("all_season_threshold_3", 180000):
                return 3.0
            elif total_km <= t.get("all_season_threshold_4", 240000):
                return 4.0
            elif total_km <= t.get("all_season_threshold_5", 300000):
                return 5.0
            else:
                return 6.0
        else:
            if total_km <= t.get("season_threshold_1", 120000):
                return 1.0
            elif total_km <= t.get("season_threshold_2", 180000):
                return 2.0
            elif total_km <= t.get("season_threshold_3", 240000):
                return 3.0
            elif total_km <= t.get("season_threshold_4", 300000):
                return 4.0
            else:
                return 5.0

    def _get_total_hardware_cost(self, total_km: int, sets_needed: float) -> float:
        """Pobierałączny koszt opon. Jeśli automat wyłączony - mnoży sztywno. W przeciwnym razie proporcja."""
        if self.sets_needed_override is not None:
            return self.tire_set_price * self.sets_needed_override

        t = self.thresholds
        if self.all_season:
            base_limit = t.get("all_season_threshold_1", 60000)
            if total_km < base_limit:
                return self.tire_set_price
            else:
                result = self.tire_set_price
                result += ((total_km - base_limit) / base_limit) * self.tire_set_price
                return result
        else:
            base_limit = t.get("season_threshold_1", 120000)
            # Dzielnik proporcji w V1 to nadal 60000 dla sezonowych:
            # (Przebieg - 120 000) / 60 000
            if total_km < base_limit:
                return self.tire_set_price
            else:
                result = self.tire_set_price
                result += ((total_km - base_limit) / 60000.0) * self.tire_set_price
                return result

    def calculate_cost(self, months: int, total_km: int) -> Dict[str, Any]:
        """Kalkuluje techniczne koszty opon dla danego wariantu.

        capex_initial_set: koszt pierwszego kompletu opon → CAPEX (rata leasingowa)
        OponyNetto: pozostałe koszty opon → koszt techniczny kontraktu
        """
        if not self.z_oponami:
            return {
                "OponyNetto": 0.0,
                "Koszt1KplOpon": 0.0,
                "IloscOpon": 0.0,
                "capex_initial_set": 0.0,
                "monthly_storage": 0.0,
                "monthly_swaps": 0.0,
                "monthly_hardware": 0.0,
            }

        if months <= 0:
            months = 1
        years = months / 12.0

        sets_needed = self._get_sets_needed(total_km)
        total_hw_cost = self._get_total_hardware_cost(total_km, sets_needed)

        swaps_total = 0.0
        storage_total = 0.0

        if self.all_season:
            swaps_total = math.ceil(total_km / 60000.0) * self.swap_cost
            storage_total = 0.0
        else:
            swaps_total = self.swap_cost * years * 2
            storage_total = self.storage_cost_per_year * years * 2

        # Pierwszy komplet → CAPEX, reszta → koszt techniczny
        capex_initial = self.tire_set_price
        remaining_hw_cost = max(total_hw_cost - capex_initial, 0.0)

        wynik_netto = remaining_hw_cost + swaps_total + storage_total

        return {
            "OponyNetto": wynik_netto,
            "Koszt1KplOpon": self.tire_set_price,
            "IloscOpon": sets_needed,
            "capex_initial_set": capex_initial,
            "monthly_storage": storage_total / months,
            "monthly_swaps": swaps_total / months,
            "monthly_hardware": remaining_hw_cost / months,
        }
