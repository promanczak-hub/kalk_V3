from typing import Any, Dict, List, cast
from core.LTRKalkulator import (
    LTRKalkulator,
    get_insurance_rates_from_db,
    get_damage_coefficients_from_db,
    get_replacement_car_rate_from_db,
)
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput
from core.LTRSubCalculatorAmortyzacja import AmortyzacjaCalculator, AmortyzacjaInput
from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
)
from core.LTRSubCalculatorKosztDzienny import KosztDziennyCalculator, KosztDziennyInput
from core.LTRSubCalculatorStawka import StawkaCalculator, StawkaInput
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew
from core.LTRSubCalculatorFinanse import FinanceCalculator, FinanceInput
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator


class PipelineDebugger(LTRKalkulator):
    def __init__(self, input_data: Any, settings: Any):
        super().__init__(input_data, settings)

    def calculate_steps(
        self, months: int, overrides: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculates 12 sequential steps and returns inputs/outputs for each, allowing overrides.
        """
        steps = []

        okres_bazowy = getattr(self.input_data, "okres_bazowy", 48)
        przebieg_bazowy = getattr(self.input_data, "przebieg_bazowy", 140000)
        if okres_bazowy <= 0:
            okres_bazowy = 48

        km_per_month = przebieg_bazowy / okres_bazowy
        total_km = int(km_per_month * months)

        vehicle_capex, options_capex = self._calculate_capex()
        capex = vehicle_capex + options_capex

        # KROK 1: Opony (Op)
        tires_res = self.tires_calc.calculate_cost(months=months, total_km=total_km)

        # Obliczenia z wyników oryginalnego
        orig_tires_base = float(
            tires_res["monthly_hardware"]
            + tires_res["monthly_storage"]
            + tires_res["monthly_swaps"]
        )
        orig_tires_capex = float(tires_res["capex_initial_set"])

        # Aplikacja ew. nadpisań
        tires_base = overrides.get("step_1_tires_base", orig_tires_base)
        tires_capex = overrides.get("step_1_tires_capex", orig_tires_capex)

        tires_total = tires_base * months

        steps.append(
            {
                "step": 1,
                "name": "Opony",
                "inputs": {
                    "months": months,
                    "total_km": total_km,
                    "z_oponami": self.tires_calc.z_oponami,
                    "klasa_opony_string": self.input_data.klasa_opony_string,
                    "srednica_felgi": self.tires_calc.srednica_felgi,
                },
                "outputs": {
                    "tires_base": tires_base,
                    "tires_capex": tires_capex,
                    "tires_total": tires_total,
                    "monthly_hardware": tires_res["monthly_hardware"],
                    "monthly_storage": tires_res["monthly_storage"],
                    "monthly_swaps": tires_res["monthly_swaps"],
                },
            }
        )

        capex_for_financing = capex + tires_capex

        # KROK 2: Koszty Dodatkowe (KDod)
        add_calc = AdditionalCostsCalculator(self.settings, self.input_data, months)
        add_calc_res = add_calc.calculate_cost()

        orig_additional_costs_base = float(add_calc_res["monthly_additional_costs"])
        additional_costs_base = overrides.get("step_2_kdod", orig_additional_costs_base)
        additional_costs_total = additional_costs_base * months

        steps.append(
            {
                "step": 2,
                "name": "Koszty Dodatkowe",
                "inputs": {
                    "months": months,
                    "settings": dict(self.settings)
                    if isinstance(self.settings, dict)
                    else vars(self.settings),
                },
                "outputs": {
                    "additional_costs_base": additional_costs_base,
                    "additional_costs_total": additional_costs_total,
                },
            }
        )

        # KROK 3: Samochód Zastępczy (SZst)
        klasa_id = self.vehicle.get("klasa_wr_id", "") if self.vehicle else ""
        rc_rate = get_replacement_car_rate_from_db(klasa_id)
        rc_calc = ReplacementCarCalculator(rc_rate)  # type: ignore
        rc_res = rc_calc.calculate_cost(
            months=months, enabled=self.input_data.replacement_car_enabled
        )

        orig_rc_base = float(rc_res["monthly_replacement_car"])
        rc_base = overrides.get("step_3_szst", orig_rc_base)
        rc_total = rc_base * months

        steps.append(
            {
                "step": 3,
                "name": "Samochód Zastępczy",
                "inputs": {
                    "months": months,
                    "enabled": self.input_data.replacement_car_enabled,
                    "klasa_id": klasa_id,
                    "rc_rate": rc_rate,
                },
                "outputs": {"rc_base": rc_base, "rc_total": rc_total},
            }
        )

        # KROK 4: Serwis (Srw)
        normatywny_przebieg = getattr(self.settings, "normatywny_przebieg_mc", 2916)
        pakiet_serwisowy_val = float(getattr(self.input_data, "pakiet_serwisowy", 0.0))
        inne_koszty_val = float(
            getattr(self.input_data, "inne_koszty_serwisowania_netto", 0.0)
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

        # Legacy ops calc just mapped to new service base
        orig_service_base = service_from_new
        service_base = overrides.get("step_4_srw", orig_service_base)
        service_total = service_base * months

        steps.append(
            {
                "step": 4,
                "name": "Serwis",
                "inputs": {"service_input": vars(service_input)},
                "outputs": {
                    "service_base": service_base,
                    "service_total": service_total,
                },
            }
        )

        # KROK 5: Cena Zakupu (CAPEX)
        orig_capex_for_financing = capex_for_financing
        capex_for_financing = overrides.get("step_5_cez", orig_capex_for_financing)
        steps.append(
            {
                "step": 5,
                "name": "Cena Zakupu (CAPEX)",
                "inputs": {
                    "vehicle_capex": vehicle_capex,
                    "options_capex": options_capex,
                    "tires_capex": tires_capex,
                },
                "outputs": {"capex_for_financing": capex_for_financing},
            }
        )

        # KROK 6: Utrata Wartości (WR)
        rv_calc = LTRSubCalculatorUtrataWartosciNew(self.vehicle, self.input_data)
        base_wr_options = sum(opt.price_net for opt in self.input_data.factory_options)
        base_wr_options += sum(
            opt.price_net
            for opt in self.input_data.service_options
            if getattr(opt, "include_in_wr", False)
        )
        vat_rate = getattr(self.settings, "vat_rate", 1.23)
        if vat_rate > 10.0:
            vat_rate = 1.0 + (vat_rate / 100.0)

        rv_res = rv_calc.calculate_values(
            months=months,
            total_km=total_km,
            base_vehicle_capex_gross=vehicle_capex * vat_rate,
            options_capex_gross=(base_wr_options + tires_capex) * vat_rate,
        )

        orig_vr_samar = float(rv_res["WR"])
        orig_utrata_z_czynszem = float(
            rv_res.get(
                "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - orig_vr_samar
            )
        )
        orig_utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])

        vr_samar = float(overrides.get("step_6_wr", orig_vr_samar))

        # Jeśli WR nadpisano ale reszty utraty nie, przelicz ponownie by wzory się zgadzały:
        if "step_6_wr" in overrides:
            utrata_z_czynszem = overrides.get(
                "step_6_utrata_z_czynszem", capex_for_financing - vr_samar
            )
            utrata_bez_czynszu = overrides.get(
                "step_6_utrata_bez_czynszu", capex_for_financing - vr_samar
            )
        else:
            utrata_z_czynszem = overrides.get(
                "step_6_utrata_z_czynszem", orig_utrata_z_czynszem
            )
            utrata_bez_czynszu = overrides.get(
                "step_6_utrata_bez_czynszu", orig_utrata_bez_czynszu
            )

        steps.append(
            {
                "step": 6,
                "name": "Utrata Wartości (WR)",
                "inputs": {
                    "months": months,
                    "total_km": total_km,
                    "base_vehicle_capex_gross": vehicle_capex * vat_rate,
                    "options_capex_gross": (base_wr_options + tires_capex) * vat_rate,
                },
                "outputs": {
                    "vr_samar": vr_samar,
                    "utrata_z_czynszem": utrata_z_czynszem,
                    "utrata_bez_czynszu": utrata_bez_czynszu,
                    "rv_lo_net": rv_res["WRdlaLO"],
                },
            }
        )

        # KROK 7: Amortyzacja (Am)
        if getattr(self.input_data, "depreciation_pct", None) is not None:
            orig_procent_amortyzacji_miesiecznie = float(
                self.input_data.depreciation_pct
            )
        else:
            amort_input = AmortyzacjaInput(
                wp=capex_for_financing, wr=vr_samar, okres=months
            )
            amort_result = AmortyzacjaCalculator(amort_input).calculate()
            orig_procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

        procent_amortyzacji_miesiecznie = overrides.get(
            "step_7_am", orig_procent_amortyzacji_miesiecznie
        )

        steps.append(
            {
                "step": 7,
                "name": "Amortyzacja",
                "inputs": {
                    "capex_for_financing": capex_for_financing,
                    "vr_samar": vr_samar,
                    "months": months,
                },
                "outputs": {
                    "procent_amortyzacji_miesiecznie": procent_amortyzacji_miesiecznie
                },
            }
        )

        # KROK 8: Ubezpieczenie (Ub)
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

        orig_insurance_base = float(insurance_res["monthly_insurance"])
        insurance_base = overrides.get("step_8_ub", orig_insurance_base)
        insurance_total = insurance_base * months

        steps.append(
            {
                "step": 8,
                "name": "Ubezpieczenie",
                "inputs": {
                    "capex_for_financing": capex_for_financing,
                    "months": months,
                    "procent_amortyzacji_miesiecznie": procent_amortyzacji_miesiecznie,
                },
                "outputs": {
                    "insurance_base": insurance_base,
                    "insurance_total": insurance_total,
                },
            }
        )

        # KROK 9: Finanse (PMT) (Fi)
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

        orig_koszt_finansowy = float(finance_res.total_interest)
        orig_czynsz_inicjalny = float(finance_res.initial_deposit_net)

        koszt_finansowy = overrides.get("step_9_fi_koszt", orig_koszt_finansowy)
        czynsz_inicjalny = overrides.get("step_9_fi_czynsz", orig_czynsz_inicjalny)

        steps.append(
            {
                "step": 9,
                "name": "Finanse (PMT)",
                "inputs": vars(finance_input),
                "outputs": {
                    "koszt_finansowy": koszt_finansowy,
                    "czynsz_inicjalny": czynsz_inicjalny,
                    "monthly_pmt_net": float(finance_res.monthly_pmt_net),
                    "total_capital_repayment": float(
                        finance_res.total_capital_repayment
                    ),
                },
            }
        )

        # KROK 10: Koszt Dzienny (KDz)
        kd_input = KosztDziennyInput(
            utrata_wartosci_z_czynszem=utrata_z_czynszem,
            utrata_wartosci_bez_czynszu=utrata_bez_czynszu,
            koszt_finansowy=koszt_finansowy,
            samochod_zastepczy_netto=rc_total,
            koszty_dodatkowe_netto=additional_costs_total,
            ubezpieczenie_netto=insurance_total,
            opony_netto=tires_total,
            serwis_netto=service_total,
            suma_odsetek_bez_czynszu=koszt_finansowy,
            okres=months,
        )
        kd_result = KosztDziennyCalculator(kd_input).calculate()

        orig_koszt_mc = float(kd_result.koszt_mc)
        orig_koszt_mc_bez_czynszu = float(kd_result.koszt_mc_bez_czynszu)

        koszt_mc = overrides.get("step_10_kdz_koszt_mc", orig_koszt_mc)
        koszt_mc_bez_czynszu = overrides.get(
            "step_10_kdz_koszt_mc_bez", orig_koszt_mc_bez_czynszu
        )

        steps.append(
            {
                "step": 10,
                "name": "Koszt Dzienny",
                "inputs": vars(kd_input),
                "outputs": {
                    "koszt_mc": koszt_mc,
                    "koszt_mc_bez_czynszu": koszt_mc_bez_czynszu,
                    "koszt_dzienny": float(kd_result.koszt_dzienny),
                    "koszty_ogolem": float(kd_result.koszty_ogolem),
                },
            }
        )

        # KROK 11: Stawka (St)
        margin_pct = self.input_data.pricing_margin_pct / 100.0
        if margin_pct >= 1.0:
            margin_pct = 0.9999

        stawka_input = StawkaInput(
            koszt_mc=koszt_mc,
            koszt_mc_bez_czynszu=koszt_mc_bez_czynszu,
            utrata_wartosci_netto=utrata_z_czynszem,
            koszty_finansowe_netto=koszt_finansowy,
            ubezpieczenie_netto=insurance_total,
            samochod_zastepczy_netto=rc_total,
            koszty_dodatkowe_netto=additional_costs_total,
            opony_netto=tires_total,
            serwis_netto=service_total,
            okres=months,
            marza=margin_pct,
            czynsz_inicjalny=czynsz_inicjalny,
        )
        stawka_result = StawkaCalculator(stawka_input).calculate()

        orig_oferowana_stawka = float(stawka_result.oferowana_stawka)
        oferowana_stawka = overrides.get("step_11_st", orig_oferowana_stawka)

        steps.append(
            {
                "step": 11,
                "name": "Stawka",
                "inputs": vars(stawka_input),
                "outputs": {
                    "oferowana_stawka": oferowana_stawka,
                    "marza_mc": float(stawka_result.marza_mc),
                    "marza_na_kontrakcie": float(stawka_result.marza_na_kontrakcie),
                    "czynsz_finansowy": float(stawka_result.czynsz_finansowy),
                    "czynsz_techniczny": float(stawka_result.czynsz_techniczny),
                },
            }
        )

        # KROK 12: Budżet Marketingowy (Bm)
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

        orig_korekta_wr_maks = float(bm_result.korekta_wr_maks)
        korekta_wr_maks = overrides.get("step_12_bm", orig_korekta_wr_maks)

        steps.append(
            {
                "step": 12,
                "name": "Budżet Marketingowy",
                "inputs": vars(bm_input),
                "outputs": {"korekta_wr_maks": korekta_wr_maks},
            }
        )

        return steps
