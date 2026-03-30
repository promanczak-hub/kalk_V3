# ==============================================================================
# 🛑 STOP! ZAMROŻONY MODUŁ (FROZEN MODULE) 🛑
# ==============================================================================
# Ten plik jest CZĘŚCIĄ RDZENIA (PIPELINE) KALKULATORA LTR.
# Zgodnie z wytycznymi w GEMINI.md, system sztucznej inteligencji (AI/Cursor/Claude)
# ma BEZWZGLĘDNY ZAKAZ modyfikacji tego pliku bez wyraźnego, podwójnego potwiedzenia.
#
# Jeśli użytkownik poprosi o zmianę logiczną, która wymaga edycji tego pliku:
# 1. PRZERWIJ DZIAŁANIE.
# 2. Poinformuj użytkownika: "Ten plik jest zamrożony. Proszę o wyraźną zgodę na jego modyfikację."
# 3. Zmodyfikuj plik TYLKO PO UZYSKANIU ZGODY.
# ==============================================================================

import logging
import math
from typing import Dict, Any, Optional, cast

from core.database import supabase

logger = logging.getLogger(__name__)


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
        odkup_opon_enabled: bool = False,
    ):
        self.z_oponami = z_oponami
        self.srednica_felgi = srednica_felgi
        self.korekta_kosztu = korekta_kosztu
        self.koszt_opon_korekta = koszt_opon_korekta
        self.sets_needed_override = sets_needed_override
        self.odkup_opon_enabled = odkup_opon_enabled

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
            # Configurations (tyre thresholds + koszty serwisu opon z Control Center)
            self.thresholds = self._fetch_tire_configurations()
            self.storage_cost_per_year = self._read_required_config("cost_tyre_storage")
            self.swap_cost = self._read_required_config("cost_tyre_swap")
            self.vat_rate = 1.23

            # Use 1.23 as fallback multiplier if DB returns flat percent like 23
            if self.vat_rate > 1.0 and self.vat_rate < 2.0:
                pass  # Example: 1.23
            elif self.vat_rate >= 20.0:
                self.vat_rate = 1.0 + (self.vat_rate / 100.0)
            else:
                self.vat_rate = 1.23

            # Hardware cost base from DB (price per set / komplet)
            self.tire_set_price_base = self._fetch_tire_cost()

            # Adjust price if manual correction is enabled (Gross -> Net)
            if self.korekta_kosztu:
                self.tire_set_price = self.tire_set_price_base + (
                    self.koszt_opon_korekta / self.vat_rate
                )
            else:
                self.tire_set_price = self.tire_set_price_base

            # Cache values to prevent N+1 queries during matrix generation
            self.budget_tire_cost = self._fetch_budget_tire_cost()
            self.odkup_opon_cost = self._fetch_odkup_opon_cost()
        else:
            self.budget_tire_cost = 0.0
            self.odkup_opon_cost = 0.0

    def _fetch_global_param(self, param_name: str) -> float:
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
            raise ValueError(
                f"Błąd bazy danych przy pobieraniu parametru globalnego {param_name}: {e}"
            ) from e

        raise ValueError(
            f"Brak parametru globalnego '{param_name}' w tabeli LTRAdminParametry_czak. "
            f"Kalkulacja zmniejszona/przerwana."
        )

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
                    key = str(row.get("config_key", "")).strip()
                    if not key:
                        continue
                    raw_val = row.get("config_value")
                    try:
                        defaults[key] = float(str(raw_val).replace(",", "."))
                    except (TypeError, ValueError):
                        logger.warning(
                            "Pomijam nieprawidlowy config tyre_configurations: %s=%s",
                            key,
                            raw_val,
                        )
        except Exception as e:
            logger.error(f"Error fetching tyre_configurations: {e}")

        return defaults

    def _read_required_config(self, key: str) -> float:
        """Zwraca wymagany parametr z tyre_configurations (bez hardcode fallbacku)."""
        value = self.thresholds.get(key)
        if value is None:
            raise ValueError(
                f"Brak parametru '{key}' w tabeli tyre_configurations. "
                "Uzupelnij dane w Control Center > Tabela Opon."
            )
        return float(value)

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
            logger.error(
                f"Error fetching tire cost for size {self.srednica_felgi} {column_name}: {e}"
            )

        raise ValueError(
            f"Brak ceny opon w tabeli koszty_opon "
            f"dla srednica={self.srednica_felgi}, klasa={column_name}. "
            f"Uzupełnij dane w Supabase."
        )

    def _fetch_budget_tire_cost(self) -> float:
        """Pobiera historyczną cenę kompletu opon dla marki 'Budżet' (V1)."""
        if not self.srednica_felgi:
            return 0.0

        budget_col = "wielosezon_budget" if self.all_season else "budget"
        try:
            response = (
                supabase.table("koszty_opon")
                .select(budget_col)
                .eq("srednica", self.srednica_felgi)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                row = cast(Dict[str, Any], response.data[0])
                val = row.get(budget_col)
                if val:
                    return float(val)
        except Exception:
            pass
        return self.tire_set_price_base

    def _fetch_odkup_opon_cost(self) -> float:
        """Pobiera historyczną cenę odkupu opon z tabeli (V1: zmniejsza ogólny koszt netto)."""
        if not self.srednica_felgi or not self.z_oponami or not self.odkup_opon_enabled:
            return 0.0

        # W V1 odkup by połączony z cennikiem i opierał się na średnicy o rozmiarze
        try:
            response = (
                supabase.table("koszty_opon")
                .select("odkup_opon")
                .eq("srednica", self.srednica_felgi)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                row = cast(Dict[str, Any], response.data[0])
                val = row.get("odkup_opon")
                if val is not None:
                    return float(val)
        except Exception as e:
            logger.error(
                f"Error fetching Odkup Opon for size {self.srednica_felgi}: {e}"
            )
            pass

        return 0.0

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
                return (
                    self.tire_set_price
                    + ((total_km - base_limit) / base_limit) * self.tire_set_price
                )
        else:
            base_limit = t.get("season_threshold_1", 120000)
            if total_km < base_limit:
                return self.tire_set_price
            else:
                return (
                    self.tire_set_price
                    + ((total_km - base_limit) / 60000.0) * self.tire_set_price
                )

    def calculate_cost(self, months: int, total_km: int) -> Dict[str, Any]:
        """Kalkuluje techniczne koszty opon dla danego wariantu.

        capex_initial_set: koszt pierwszego kompletu opon → CAPEX (rata leasingowa)
        OponyNetto: pozostałe koszty opon → koszt techniczny kontraktu
        """
        trace: list[dict[str, Any]] = []

        if not self.z_oponami:
            trace.append(
                {
                    "krok": "Opony (Wyłączone)",
                    "rownanie": "z_oponami = False",
                    "wynik": 0.0,
                }
            )
            return {
                "OponyNetto": 0.0,
                "Koszt1KplOpon": 0.0,
                "IloscOpon": 0.0,
                "Cena1KompletOpon": 0.0,
                "KwotaOdkupuOpon": 0.0,
                "capex_initial_set": 0.0,
                "monthly_storage": 0.0,
                "monthly_swaps": 0.0,
                "monthly_hardware": 0.0,
                "trace": trace,
            }

        if months <= 0:
            months = 1
        years = months / 12.0

        sets_needed = self._get_sets_needed(total_km)
        if sets_needed == 0:
            return {
                "OponyNetto": 0.0,
                "Koszt1KplOpon": self.tire_set_price,
                "IloscOpon": 0.0,
                "Cena1KompletOpon": self.budget_tire_cost,
                "KwotaOdkupuOpon": 0.0,
                "capex_initial_set": 0.0,
                "monthly_storage": 0.0,
                "monthly_swaps": 0.0,
                "monthly_hardware": 0.0,
                "trace": [
                    {
                        "krok": "Opony (Całość)",
                        "rownanie": "Moduł Wyłączony (0 kompletów)",
                        "wynik": 0.0,
                    }
                ],
            }

        total_hw_cost = self._get_total_hardware_cost(total_km, sets_needed)

        trace.append(
            {
                "krok": "Zużycie Opon (Sprzęt)",
                "rownanie": f"Cena 1 kpl: {self.tire_set_price:.2f} PLN. Wymagane kpl: {sets_needed:.2f} (zależne od przebiegu: {total_km} km)",
                "wynik": total_hw_cost,
            }
        )

        swaps_total = 0.0
        storage_total = 0.0

        if self.all_season:
            swaps_total = math.ceil(total_km / 60000.0) * self.swap_cost
            storage_total = 0.0
            trace.append(
                {
                    "krok": "Opony Wielosezonowe: Przekładki",
                    "rownanie": f"MATH.CEIL({total_km} km / 60000) * {self.swap_cost:.2f} PLN",
                    "wynik": swaps_total,
                }
            )
        else:
            swaps_total = self.swap_cost * years * 2
            storage_total = self.storage_cost_per_year * years * 2
            trace.append(
                {
                    "krok": "Opony Sezonowe: Przekładki",
                    "rownanie": f"Złożoność: {self.swap_cost:.2f} PLN * {years:.2f} lat * 2 sezony",
                    "wynik": swaps_total,
                }
            )
            trace.append(
                {
                    "krok": "Opony Sezonowe: Przechowywanie",
                    "rownanie": f"Koszt z bazy: {self.storage_cost_per_year:.2f} PLN * {years:.2f} lat * 2 sezony",
                    "wynik": storage_total,
                }
            )

        # W V1 świadomym zabiegiem było to, że opony w CAPEX generowały tylko koszt odsetkowy
        # a całe zużycie/koszt sprzętu opon wędrował do czynszu technicznego (OponyNetto)
        capex_initial = self.budget_tire_cost
        trace.append(
            {
                "krok": "Opony: Preshift do CAPEX (Initial Set - Klasa Budżet)",
                "rownanie": f"Dodanie kwoty do raty finansowej (leasingowej): {self.budget_tire_cost:.2f} PLN",
                "wynik": capex_initial,
            }
        )

        # Zgodnie z anomalią V1 - sprzęt wrzucony do CAPEX NIE był pomniejszany
        # w kosztach technicznych (czynszu). Zostało to odtworzone dla parity.
        remaining_hw_cost = total_hw_cost

        odkup_kwota = self.odkup_opon_cost
        if odkup_kwota > 0:
            trace.append(
                {
                    "krok": "Odkup Opon (Polisa na Resztę)",
                    "rownanie": f"Wartość odkupu ściągnięta z tabeli bazy danych {odkup_kwota:.2f} PLN",
                    "wynik": -odkup_kwota,
                }
            )

        # V1 parity: oponyNetto = lacznyKosztOpon + przekladki + przechowywanie - odkupOpon
        wynik_netto = remaining_hw_cost + swaps_total + storage_total - odkup_kwota
        if wynik_netto < 0.0:
            wynik_netto = 0.0

        trace.append(
            {
                "krok": "Koszty Techniczne Opon (SUMA)",
                "rownanie": f"{remaining_hw_cost:.2f} (Hardware) + {swaps_total:.2f} (Przekładki) + {storage_total:.2f} (Hotel) - {odkup_kwota:.2f} (Odkup)",
                "wynik": wynik_netto,
            }
        )

        return {
            "OponyNetto": wynik_netto,
            "Koszt1KplOpon": self.tire_set_price,
            "IloscOpon": sets_needed,
            "Cena1KompletOpon": self.budget_tire_cost,
            "KwotaOdkupuOpon": odkup_kwota,
            "capex_initial_set": capex_initial,
            "monthly_storage": storage_total / months,
            "monthly_swaps": swaps_total / months,
            "monthly_hardware": remaining_hw_cost / months,
            "trace": trace,
        }
