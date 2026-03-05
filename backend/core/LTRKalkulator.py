from typing import List, Dict, Any, cast, Tuple
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony
from core.operations import OperationalCostsCalculator
from core.LTRSubCalculatorFinanse import FinanceCalculator, FinanceInput
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput
from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator,
    PurchasePriceInput,
    PurchasePriceOption,
)
from core.LTRSubCalculatorAmortyzacja import (
    AmortyzacjaCalculator,
    AmortyzacjaInput,
)
from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
)
from core.LTRSubCalculatorKosztDzienny import (
    KosztDziennyCalculator,
    KosztDziennyInput,
)
from core.LTRSubCalculatorStawka import (
    StawkaCalculator,
    StawkaInput,
)
from functools import lru_cache


@lru_cache(maxsize=128)
def get_vehicle_from_db(vid: str) -> Dict[str, Any]:
    """Dodatkowa f-cja do pobrania auta z DB na podst vehicle_id"""
    if not vid:
        return {}
    try:
        from core.database import supabase

        res = supabase.table("pojazdy_master").select("*").eq("id", vid).execute()
        if res.data and isinstance(res.data, list) and len(res.data) > 0:
            res_dict = cast(Dict[str, Any], res.data[0])
            return res_dict
    except Exception:
        pass
    return cast(Dict[str, Any], {})


@lru_cache(maxsize=128)
def get_samar_klasa_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera parametry serwisowe (i nie tylko) przypisane do klasy pojazdu"""
    if not klasa_id:
        return {}
    try:
        from core.database import supabase

        res = supabase.table("samar_klasa_wr").select("*").eq("id", klasa_id).execute()
        if res.data and len(res.data) > 0:
            return cast(Dict[str, Any], res.data[0])
    except Exception:
        pass
    return {}


@lru_cache(maxsize=128)
def get_insurance_rates_from_db(klasa_id: str) -> List[Dict[str, Any]]:
    """Pobiera tabelę ubezpieczeń dla danej klasy (lub domyślnej null)"""
    try:
        from core.database import supabase

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


@lru_cache(maxsize=128)
def get_replacement_car_rate_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera parametry auta zastępczego z tabeli replacement_car_rates"""
    try:
        from core.database import supabase

        # Pobierz z replacement_car_rates dla konkretnej klasy SAMAR
        if klasa_id:
            res = (
                supabase.table("replacement_car_rates")
                .select("*")
                .eq("samar_class_id", klasa_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])

        # Fallback: brak danych dla tej klasy — zwróć pusty dict (koszt = 0)
    except Exception as e:
        print(f"Error fetching replacement car rate: {e}")
    return {}


@lru_cache(maxsize=128)
def get_damage_coefficients_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera współczynniki szkodowe dla klasy pojazdu"""
    try:
        from core.database import supabase

        # Pobierz dla konkretnej klasy
        if klasa_id:
            res = (
                supabase.table("ltr_admin_wspolczynniki_szkodowe")
                .select("*")
                .eq("klasa_wr_id", klasa_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])

        # Fallback dla null / default
        res = (
            supabase.table("ltr_admin_wspolczynniki_szkodowe")
            .select("*")
            .is_("klasa_wr_id", "null")
            .execute()
        )
        if res.data:
            return cast(Dict[str, Any], res.data[0])
    except Exception as e:
        print(f"Error fetching damage coefficients: {e}")
    return {}


class LTRKalkulator:
    """Rdzeń budujący Matrix dla zadanego CalculatorInput"""

    def __init__(self, input_data: Any, settings: Any):
        self.input_data = input_data
        self.settings = settings

        # Inicjalizacja subkalkulatorów
        self.tires_calc = LTRSubCalculatorOpony(
            z_oponami=getattr(self.input_data, "z_oponami", True),
            klasa_opony_string=getattr(self.input_data, "klasa_opony_string", ""),
            srednica_felgi=getattr(self.input_data, "srednica_felgi", 0) or 0,
            korekta_kosztu=getattr(self.input_data, "korekta_kosztu_opon", False),
            koszt_opon_korekta=getattr(self.input_data, "koszt_opon_korekta", 0.0),
            sets_needed_override=getattr(
                self.input_data, "liczba_kompletow_opon", None
            ),
        )

        # Load vehicle if needed
        vid = getattr(self.input_data, "vehicle_id", "")
        if isinstance(self.input_data, dict):
            vid = self.input_data.get("vehicle_id", "")
        self.vehicle = get_vehicle_from_db(vid) if vid else {}

        klasa_id = self.vehicle.get("klasa_wr_id", "")
        self.samar_klasa = get_samar_klasa_from_db(klasa_id) if klasa_id else {}

        self.ops_calc = OperationalCostsCalculator(samar_klasa_data=self.samar_klasa)
        # Service calculator (ASO/nonASO) — replaces ops_calc for service cost component
        self.service_cost_type = getattr(self.input_data, "service_cost_type", "ASO")
        # Map frontend "nonASO" → backend pattern "NON-ASO"
        self._opcja_serwisowa = (
            "NON-ASO" if self.service_cost_type == "nonASO" else "ASO"
        )

    def _calculate_capex(self) -> Tuple[float, float]:
        """Kalkuluje wejściową sumę finansowaną (CAPEX) autorskim kalkulatorem (V3)"""
        base_net = self.input_data.base_price_net

        options = []
        for opt in self.input_data.factory_options:
            options.append(
                PurchasePriceOption(
                    price_net=opt.price_net,
                    name=opt.name,
                    is_service=False,
                    is_discountable=not opt.no_discount,
                )
            )

        for opt in self.input_data.service_options:
            options.append(
                PurchasePriceOption(
                    price_net=opt.price_net,
                    name=opt.name,
                    is_service=True,
                    is_discountable=not opt.no_discount,
                )
            )

        # W nowej architekturze V3 moduł GSM zawsze doliczany jest do Ceny Zakupu.
        gsm_cost = self.settings.cost_gsm_device + self.settings.cost_gsm_installation

        pp_input = PurchasePriceInput(
            base_price_net=base_net,
            options=options,
            discount_pct=self.input_data.discount_pct,
            add_gsm_device=True,
            gsm_hardware_cost=gsm_cost,
            pakiet_serwisowy_net=float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            ),
        )

        calc = PurchasePriceCalculator(pp_input)
        res = calc.calculate()

        return res.discounted_base, res.total_options_capex

    def build_matrix(self) -> List[Dict[str, Any]]:
        """Przelicza wszystkie warianty i zwraca siatkę (List of Cells)"""
        # V3 Matrix Generation: Linear 1D Grid (6 - 84 months) based on reference usage (Card Summary)
        okres_bazowy = getattr(self.input_data, "okres_bazowy", 48)
        przebieg_bazowy = getattr(self.input_data, "przebieg_bazowy", 140000)

        if okres_bazowy <= 0:
            okres_bazowy = 48

        # Obliczenie wskaźnika stałego zużycia na miesiąc
        km_per_month = przebieg_bazowy / okres_bazowy

        cells = []

        vehicle_capex, options_capex = self._calculate_capex()
        capex = vehicle_capex + options_capex

        # Instantiate RV calculator once (shared across all months)
        from core.LTRSubCalculatorUtrataWartosciNew import (
            LTRSubCalculatorUtrataWartosciNew,
        )

        rv_calc = LTRSubCalculatorUtrataWartosciNew(self.vehicle, self.input_data)

        # Opcje pod Wartość Rezydualną (Zawsze Fabryczne + Serwisowe z include_in_wr)
        base_wr_options = sum(opt.price_net for opt in self.input_data.factory_options)
        base_wr_options += sum(
            opt.price_net
            for opt in self.input_data.service_options
            if getattr(opt, "include_in_wr", False)
        )

        # Raw margin percentage (e.g. 2.0%)
        margin_pct = self.input_data.pricing_margin_pct / 100.0
        if margin_pct >= 1.0:
            margin_pct = 0.9999  # Prevention of division by zero

        for months in range(6, 85, 6):
            total_km = int(km_per_month * months)
            km_per_year = int(12 * total_km / months) if months > 0 else 0

            # 1. Koszty Opon
            tires_res = self.tires_calc.calculate_cost(months=months, total_km=total_km)
            capex_for_financing = (
                capex + tires_res["capex_initial_set"]
            )  # Wartość opony do rat

            # 2. Koszty Techniczne/Operacyjne (legacy — kept for fallback)
            ops_res = self.ops_calc.calculate_cost(
                months=months, total_km=total_km, capex=capex_for_financing
            )

            # 3. Finansowanie i Utrata Wartości (SAMAR SQL Subcalculator / UtrataWartosciNew)

            # VAT Rate to apply gross math
            vat_rate = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate > 10.0:
                vat_rate = 1.0 + (vat_rate / 100.0)

            # Obliczamy Wartość Końcową (RV)
            rv_res = rv_calc.calculate_values(
                months=months,
                total_km=total_km,
                base_vehicle_capex_gross=vehicle_capex * vat_rate,
                options_capex_gross=(base_wr_options + tires_res["capex_initial_set"])
                * vat_rate,
            )

            vr_samar = rv_res["WR"]

            # Obliczenie PMT TDD V1
            finance_input = FinanceInput(
                total_capex=capex_for_financing,
                upfront_pct=self.input_data.initial_deposit_pct,
                rv_net=vr_samar,
                months=months,
                wibor_pct=self.input_data.wibor_pct,
                margin_pct=self.input_data.margin_pct,
            )
            finance_calc = FinanceCalculator(finance_input)
            finance_res = finance_calc.calculate()

            # Wynik Opon z dict
            tires_base = float(
                tires_res["monthly_hardware"]
                + tires_res["monthly_storage"]
                + tires_res["monthly_swaps"]
            )
            # Wynik Serwisu — nowy ServiceCalculator (ASO/nonASO z DB + floor normatywnego przebiegu)
            normatywny_przebieg = getattr(self.settings, "normatywny_przebieg_mc", 2916)
            pakiet_serwisowy_val = float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            )
            inne_koszty_val = float(
                getattr(
                    self.input_data,
                    "inne_koszty_serwisowania_netto",
                    0.0,
                )
            )
            service_input = ServiceCalculatorInput(
                z_serwisem=True,
                opcja_serwisowa=self._opcja_serwisowa,
                normatywny_przebieg_mc=normatywny_przebieg,
                samar_class_id=int(self.vehicle.get("klasa_wr_id", 0))
                if self.vehicle
                else 0,
                engine_type_id=int(self.vehicle.get("engine_type_id", 1))
                if self.vehicle
                else 1,
                power_kw=float(self.vehicle.get("power_kw", 100))
                if self.vehicle
                else 100.0,
                przebieg=total_km,
                okres=months,
                pakiet_serwisowy=pakiet_serwisowy_val,
                inne_koszty_serwisowania_netto=inne_koszty_val,
            )
            service_calc = ServiceCalculator(service_input)
            service_from_new = service_calc.calculate()
            # Use new calculator result if > 0, otherwise fallback to legacy ops_calc
            service_base = (
                service_from_new
                if service_from_new > 0
                else float(ops_res["monthly_service"])
            )

            # --- SUB-KALKULATOR: AMORTYZACJA (V1 port) ---
            if getattr(self.input_data, "depreciation_pct", None) is not None:
                procent_amortyzacji_miesiecznie = float(
                    self.input_data.depreciation_pct
                )
            else:
                amort_input = AmortyzacjaInput(
                    wp=capex_for_financing, wr=vr_samar, okres=months
                )
                amort_result = AmortyzacjaCalculator(amort_input).calculate()
                procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

            # --- SUB-KALKULATOR: UBEZPIECZENIE ---
            klasa_id = self.vehicle.get("klasa_wr_id", "") if self.vehicle else ""
            insurance_rates = get_insurance_rates_from_db(klasa_id)
            damage_coeffs = get_damage_coefficients_from_db(klasa_id)
            ins_calc = InsuranceCalculator(
                insurance_rates=insurance_rates,  # type: ignore
                damage_coefficients=damage_coeffs,  # type: ignore
                settings=self.settings,  # type: ignore
                amortization_pct=procent_amortyzacji_miesiecznie,  # type: ignore
                total_km=total_km,  # type: ignore
            )

            insurance_res = ins_calc.calculate_cost(months, capex_for_financing)  # type: ignore
            insurance_base = float(insurance_res["monthly_insurance"])
            insurance_total = float(
                insurance_res.get("total_insurance", insurance_base * months)
            )

            # --- SUB-KALKULATOR: SAMOCHÓD ZASTĘPCZY ---
            rc_rate = get_replacement_car_rate_from_db(klasa_id)
            rc_calc = ReplacementCarCalculator(rc_rate)  # type: ignore
            rc_res = rc_calc.calculate_cost(
                months=months, enabled=self.input_data.replacement_car_enabled
            )
            rc_base = float(rc_res["monthly_replacement_car"])
            rc_total = float(rc_res.get("total_replacement_car", rc_base * months))

            # --- SUB-KALKULATOR: KOSZTY DODATKOWE ---
            add_calc = AdditionalCostsCalculator(self.settings, self.input_data, months)
            add_calc_res = add_calc.calculate_cost()
            additional_costs_base = float(add_calc_res["monthly_additional_costs"])
            additional_costs_total = additional_costs_base * months

            # Totale do sub-kalkulatorów V1
            tires_total = tires_base * months
            service_total = service_base * months
            utrata_z_czynszem = float(
                rv_res.get(
                    "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - vr_samar
                )
            )
            utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])

            # --- SUB-KALKULATOR: KOSZT DZIENNY (V1 port) ---
            kd_input = KosztDziennyInput(
                utrata_wartosci_z_czynszem=utrata_z_czynszem,
                utrata_wartosci_bez_czynszu=utrata_bez_czynszu,
                koszt_finansowy=finance_res.total_interest,
                samochod_zastepczy_netto=rc_total,
                koszty_dodatkowe_netto=additional_costs_total,
                ubezpieczenie_netto=insurance_total,
                opony_netto=tires_total,
                serwis_netto=service_total,
                suma_odsetek_bez_czynszu=finance_res.total_interest,
                okres=months,
            )
            kd_result = KosztDziennyCalculator(kd_input).calculate()

            # --- SUB-KALKULATOR: STAWKA (V1 port – pełny rozkład marży) ---
            stawka_input = StawkaInput(
                koszt_mc=kd_result.koszt_mc,
                koszt_mc_bez_czynszu=kd_result.koszt_mc_bez_czynszu,
                utrata_wartosci_netto=utrata_z_czynszem,
                koszty_finansowe_netto=finance_res.total_interest,
                ubezpieczenie_netto=insurance_total,
                samochod_zastepczy_netto=rc_total,
                koszty_dodatkowe_netto=additional_costs_total,
                opony_netto=tires_total,
                serwis_netto=service_total,
                okres=months,
                marza=margin_pct,
                czynsz_inicjalny=float(finance_res.initial_deposit_net),
            )
            stawka_result = StawkaCalculator(stawka_input).calculate()

            # --- SUB-KALKULATOR: BUDŻET MARKETINGOWY (V1 port) ---
            vat_rate_mult = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_mult > 10.0:
                vat_rate_mult = 1.0 + (vat_rate_mult / 100.0)
            budzet_mktg_ltr = getattr(self.settings, "budzet_marketingowy_ltr", 0.0)
            bm_input = BudzetMarketingowyInput(
                wr_przewidywana_cena_sprzedazy=vr_samar,
                stawka_vat=vat_rate_mult,
                budzet_marketingowy_ltr=budzet_mktg_ltr,
            )
            bm_result = BudzetMarketingowyCalculator(bm_input).calculate()

            # Wyniki z nowego StawkaCalculator
            total_base = kd_result.koszt_mc
            total_price = stawka_result.oferowana_stawka

            cells.append(
                {
                    "months": months,
                    "km_per_year": km_per_year,
                    "total_km": total_km,
                    "base_cost_net": round(total_base, 2),
                    "price_net": round(total_price, 2),
                    "rv_samar_net": round(vr_samar, 2),
                    "rv_lo_net": round(rv_res["WRdlaLO"], 2),
                    "utrata_wartosci_bez_czynszu_net": round(
                        rv_res["UtrataWartosciBEZczynszu"], 2
                    ),
                    # Nowe pola V1
                    "koszt_dzienny": round(kd_result.koszt_dzienny, 2),
                    "koszty_ogolem": round(kd_result.koszty_ogolem, 2),
                    "amortyzacja_pct": round(procent_amortyzacji_miesiecznie, 6),
                    "korekta_wr_maks": round(bm_result.korekta_wr_maks, 2),
                    "marza_mc": round(stawka_result.marza_mc, 2),
                    "marza_na_kontrakcie": round(stawka_result.marza_na_kontrakcie, 2),
                    "marza_na_kontrakcie_pct": round(
                        stawka_result.marza_na_kontrakcie_procent, 6
                    ),
                    "czynsz_finansowy": round(stawka_result.czynsz_finansowy, 2),
                    "czynsz_techniczny": round(stawka_result.czynsz_techniczny, 2),
                    "breakdown": {
                        "finance": {
                            "base": round(stawka_result.koszt_finansowy.koszt_mc, 2),
                            "margin": round(
                                stawka_result.koszt_finansowy.kwota_marzy_korekta, 2
                            ),
                            "price": round(
                                stawka_result.koszt_finansowy.koszt_plus_marza_korekta,
                                2,
                            ),
                            "monthly_pmt": round(finance_res.monthly_pmt_net, 2),
                            "total_interest": finance_res.total_interest,
                            "total_capital_repayment": finance_res.total_capital_repayment,
                            "initial_deposit_net": finance_res.initial_deposit_net,
                            "rozklad_marzy": round(
                                stawka_result.koszt_finansowy.rozklad_marzy, 4
                            ),
                        },
                        "technical": {
                            "service": {
                                "base": round(stawka_result.koszt_serwis.koszt_mc, 2),
                                "margin": round(
                                    stawka_result.koszt_serwis.kwota_marzy_korekta, 2
                                ),
                                "price": round(
                                    stawka_result.koszt_serwis.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_serwis.rozklad_marzy, 4
                                ),
                            },
                            "tires": {
                                "base": round(stawka_result.koszt_opony.koszt_mc, 2),
                                "margin": round(
                                    stawka_result.koszt_opony.kwota_marzy_korekta, 2
                                ),
                                "price": round(
                                    stawka_result.koszt_opony.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_opony.rozklad_marzy, 4
                                ),
                            },
                            "insurance": {
                                "base": round(
                                    stawka_result.koszt_ubezpieczenie.koszt_mc, 2
                                ),
                                "margin": round(
                                    stawka_result.koszt_ubezpieczenie.kwota_marzy_korekta,
                                    2,
                                ),
                                "price": round(
                                    stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_ubezpieczenie.rozklad_marzy, 4
                                ),
                            },
                            "replacement_car": {
                                "base": round(
                                    stawka_result.koszt_samochod_zastepczy.koszt_mc, 2
                                ),
                                "margin": round(
                                    stawka_result.koszt_samochod_zastepczy.kwota_marzy_korekta,
                                    2,
                                ),
                                "price": round(
                                    stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_samochod_zastepczy.rozklad_marzy,
                                    4,
                                ),
                            },
                            "additional_costs": {
                                "base": round(stawka_result.koszt_admin.koszt_mc, 2),
                                "margin": round(
                                    stawka_result.koszt_admin.kwota_marzy_korekta, 2
                                ),
                                "price": round(
                                    stawka_result.koszt_admin.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_admin.rozklad_marzy, 4
                                ),
                            },
                        },
                    },
                    "status": "OK" if total_km <= 200000 else "WARNING_HIGH_KM",
                }
            )

        return cells
