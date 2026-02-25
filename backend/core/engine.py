from typing import List, Dict, Any, cast, Tuple
from core.tires import LTRSubCalculatorOpony
from core.operations import OperationalCostsCalculator
from core.finance import FinancialCostsCalculator
from core.insurance import InsuranceCalculator
from core.replacement_car import ReplacementCarCalculator
from core.additional_costs import AdditionalCostsCalculator


class CalculationEngine:
    """Rdzeń budujący Matrix dla zadanego CalculatorInput"""

    def __init__(self, input_data: Any, settings: Any):
        self.input_data = input_data
        self.settings = settings

        # Inicjalizacja subkalkulatorów
        self.tires_calc = LTRSubCalculatorOpony(
            all_season_tires=self.input_data.all_season_tires,
            tire_buyback=self.input_data.tire_buyback,
        )

        # Load vehicle if needed
        self.vehicle = self._get_vehicle()
        self.samar_klasa = self._get_samar_klasa()

        self.ops_calc = OperationalCostsCalculator(samar_klasa_data=self.samar_klasa)
        self.finance_calc = FinancialCostsCalculator(
            wibor_pct=self.input_data.wibor_pct,
            margin_pct=self.input_data.margin_pct,
            initial_deposit_pct=self.input_data.initial_deposit_pct,
        )

    def _get_vehicle(self) -> Dict[str, Any]:
        """Dodatkowa f-cja do pobrania auta z DB na podst vehicle_id"""
        from core.database import supabase

        vid = self.input_data.vehicle_id
        if not vid:
            return {}
        try:
            res = supabase.table("pojazdy_master").select("*").eq("id", vid).execute()
            if res.data and isinstance(res.data, list) and len(res.data) > 0:
                res_dict = cast(Dict[str, Any], res.data[0])
                return res_dict
        except Exception:
            pass
        return cast(Dict[str, Any], {})

    def _get_samar_klasa(self) -> Dict[str, Any]:
        """Pobiera parametry serwisowe (i nie tylko) przypisane do klasy pojazdu"""
        klasa_id = self.vehicle.get("klasa_wr_id")
        if not klasa_id:
            return {}
        try:
            from core.database import supabase

            res = (
                supabase.table("samar_klasa_wr")
                .select("*")
                .eq("id", klasa_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])
        except Exception:
            pass
        return {}

    def _get_insurance_rates(self) -> List[Dict[str, Any]]:
        """Pobiera tabelę ubezpieczeń dla danej klasy (lub domyślnej null)"""
        try:
            from core.database import supabase

            klasa_id = self.vehicle.get("klasa_wr_id")

            # Pobierz dla konkretnej klasy
            if klasa_id:
                res = (
                    supabase.table("ltr_admin_ubezpieczenia")
                    .select("*")
                    .eq("KlasaId", klasa_id)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return cast(List[Dict[str, Any]], res.data)

            # Fallback dla null / default
            res = (
                supabase.table("ltr_admin_ubezpieczenia")
                .select("*")
                .is_("KlasaId", "null")
                .execute()
            )
            if res.data:
                return cast(List[Dict[str, Any]], res.data)
        except Exception as e:
            print(f"Error fetching insurance rates: {e}")
        return []

    def _get_replacement_car_rate(self) -> Dict[str, Any]:
        """Pobiera parametry auta zastępczego dla klasy pojazdu"""
        try:
            from core.database import supabase

            klasa_id = self.vehicle.get("klasa_wr_id")

            # Pobierz dla konkretnej klasy
            if klasa_id:
                res = (
                    supabase.table("ltr_admin_stawka_zastepczy")
                    .select("*")
                    .eq("KlasaId", klasa_id)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return cast(Dict[str, Any], res.data[0])

            # Fallback dla null / default
            res = (
                supabase.table("ltr_admin_stawka_zastepczy")
                .select("*")
                .is_("KlasaId", "null")
                .execute()
            )
            if res.data:
                return cast(Dict[str, Any], res.data[0])
        except Exception as e:
            print(f"Error fetching replacement car rate: {e}")
        return {}

    def _calculate_capex(self) -> Tuple[float, float]:
        """Kalkuluje wejściową sumę finansowaną (CAPEX) uwzględniając rabaty i opcje z UI"""
        base_net = self.input_data.base_price_net

        # Aplikuj globalny rabat pojazdu tylko na bazę!
        discount_multiplier = 1.0 - (self.input_data.discount_pct / 100.0)
        vehicle_discounted = base_net * discount_multiplier

        # Opcje powiększają CAPEX (fabryczne vs dealerskie/serwisowe)
        options_total = 0.0
        for opt in self.input_data.factory_options + self.input_data.service_options:
            if opt.no_discount:
                options_total += opt.price_net
            else:
                options_total += opt.price_net * discount_multiplier

        # Dodanie kosztu urządzenia GPS i montażu do CAPEX (zgodnie z logiką V1 LTRSubCalculatorCenaZakupu)
        if self.input_data.add_gsm_subscription:
            options_total += self.settings.cost_gsm_device
            options_total += self.settings.cost_gsm_installation

        return vehicle_discounted, options_total

    def build_matrix(self) -> List[Dict[str, Any]]:
        """Przelicza wszystkie warianty i zwraca siatkę (List of Cells)"""
        grid = self.input_data.grid
        cells = []

        vehicle_capex, options_capex = self._calculate_capex()
        capex = vehicle_capex + options_capex

        # Raw margin percentage (e.g. 2.0%)
        margin_pct = self.input_data.pricing_margin_pct / 100.0
        if margin_pct >= 1.0:
            margin_pct = 0.9999  # Prevention of division by zero

        for months in grid.months:
            for km_per_year in grid.km_per_year:
                total_km = int(km_per_year * (months / 12.0))

                # 1. Koszty Opon
                tires_res = self.tires_calc.calculate_cost(
                    months=months, total_km=total_km
                )
                capex_for_financing = (
                    capex + tires_res["capex_initial_set"]
                )  # Wartość opony do rat

                # 2. Koszty Techniczne/Operacyjne
                ops_res = self.ops_calc.calculate_cost(
                    months=months, total_km=total_km, capex=capex_for_financing
                )

                # 3. Finansowanie i Utrata Wartości (SAMAR SQL Subcalculator)
                from core.samar_rv import SamarRVCalculator

                samar_calc = SamarRVCalculator(self.vehicle, self.input_data)

                # Obliczamy Wartość Końcową (RV) na podstawie danych z bazy SAMAR
                # Przekazujemy cenę bazową powiększoną o opony (capex_for_financing)
                vr_samar = samar_calc.calculate_rv(
                    months=months,
                    total_km=total_km,
                    base_vehicle_capex=vehicle_capex,
                    options_capex=options_capex + tires_res["capex_initial_set"],
                )

                # Obliczenie PMT
                finance_res = self.finance_calc.calculate_cost(
                    months=months, capex=capex_for_financing, rv_net=vr_samar
                )

                finance_base = float(finance_res["monthly_pmt"])

                # Wynik Opon z dict
                tires_base = float(
                    tires_res["monthly_hardware"]
                    + tires_res["monthly_storage"]
                    + tires_res["monthly_swaps"]
                )
                # Wynik Serwisu z dict
                service_base = float(ops_res["monthly_service"])

                tech_base = tires_base + service_base

                # Obliczanie Ubezpieczenia 7-letniego loopem
                # Amortyzacja liniowa
                utrata_wartosci = capex_for_financing - vr_samar
                kwota_amortyzacji_1_miesiac = float(
                    utrata_wartosci / months if months > 0 else 0
                )
                procent_amortyzacji_miesiecznie = float(
                    kwota_amortyzacji_1_miesiac / capex_for_financing
                    if capex_for_financing > 0
                    else 0
                )

                insurance_rates = self._get_insurance_rates()
                ins_calc = InsuranceCalculator(
                    insurance_rates, procent_amortyzacji_miesiecznie
                )

                insurance_res = ins_calc.calculate_cost(months, capex_for_financing)
                insurance_base = float(insurance_res["monthly_insurance"])

                # Obliczanie Auta Zastępczego
                rc_rate = self._get_replacement_car_rate()
                rc_calc = ReplacementCarCalculator(rc_rate)
                rc_res = rc_calc.calculate_cost(
                    months=months, enabled=self.input_data.replacement_car_enabled
                )
                rc_base = float(rc_res["monthly_replacement_car"])

                # Koszty Dodatkowe
                add_calc = AdditionalCostsCalculator(
                    self.settings, self.input_data, months
                )
                add_calc_res = add_calc.calculate_cost()
                additional_costs_base = float(add_calc_res["monthly_additional_costs"])

                # V1 Advanced Margin Spreading (Zaawansowany Podział Marży)
                # Krok 1: Suma baz netto
                total_base = (
                    finance_base
                    + tech_base
                    + insurance_base
                    + rc_base
                    + additional_costs_base
                )

                # Krok 2: Całkowity zysk (Marza MC) -> podstawaMarzy * (1 / (1 - marza)) - podstawaMarzy
                total_product_margin = 0.0
                if total_base > 0:
                    total_product_margin = (
                        total_base * (1.0 / (1.0 - margin_pct)) - total_base
                    )

                total_price = total_base + total_product_margin

                # Krok 3: Proporcjonalne przydzielenie marży (Waga CostBase / TotalBase)
                def spread(cost_base: float) -> float:
                    if total_base == 0:
                        return 0.0
                    weight = cost_base / total_base
                    return round(total_product_margin * weight, 2)

                finance_margin = spread(finance_base)
                service_margin = spread(service_base)
                tires_margin = spread(tires_base)
                insurance_margin = spread(insurance_base)
                rc_margin = spread(rc_base)
                ac_margin = spread(additional_costs_base)

                cells.append(
                    {
                        "months": months,
                        "km_per_year": km_per_year,
                        "total_km": total_km,
                        "base_cost_net": round(total_base, 2),
                        "price_net": round(total_price, 2),
                        "breakdown": {
                            "finance": {
                                "base": round(finance_base, 2),
                                "margin": finance_margin,
                                "price": round(finance_base + finance_margin, 2),
                                "monthly_pmt": finance_res["monthly_pmt"],
                                "total_interest": finance_res["total_interest"],
                                "total_capital_repayment": finance_res[
                                    "total_capital_repayment"
                                ],
                                "initial_deposit_net": finance_res[
                                    "initial_deposit_net"
                                ],
                            },
                            "technical": {
                                "service": {
                                    "base": round(service_base, 2),
                                    "margin": service_margin,
                                    "price": round(service_base + service_margin, 2),
                                },
                                "tires": {
                                    "base": round(tires_base, 2),
                                    "margin": tires_margin,
                                    "price": round(
                                        tires_res["total_monthly_tire_cost"]
                                        + tires_margin,
                                        2,
                                    ),
                                },
                                "insurance": {
                                    "base": round(insurance_base, 2),
                                    "margin": insurance_margin,
                                    "price": round(
                                        insurance_base + insurance_margin, 2
                                    ),
                                },
                                "replacement_car": {
                                    "base": round(rc_base, 2),
                                    "margin": rc_margin,
                                    "price": round(rc_base + rc_margin, 2),
                                },
                                "additional_costs": {
                                    "base": round(additional_costs_base, 2),
                                    "margin": ac_margin,
                                    "price": round(
                                        additional_costs_base + ac_margin, 2
                                    ),
                                },
                            },
                        },
                        "status": "OK" if total_km <= 200000 else "WARNING_HIGH_KM",
                    }
                )

        return cells
