import json
from html import escape
from typing import Any, Dict, List
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
from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput
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

        vehicle_capex, options_capex, capex_res = self._calculate_capex()
        capex = vehicle_capex + options_capex
        # V1 parity: WR curve uses FULL catalogue prices (no discount)
        # vehicle_capex = discounted_base (for financing),
        # but WR needs base_price_net (full catalogue) for depreciation curve
        base_price_net_full = float(getattr(self.input_data, "base_price_net", 0))

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
                    "klasa_opony_string": getattr(self.input_data, "klasa_opony_string", ""),
                    "srednica_felgi": getattr(self.tires_calc, "srednica_felgi", 0),
                },
                "outputs": {
                    "OponyNetto": float(tires_res.get("OponyNetto", 0.0)),
                    "Koszt1KplOpon": float(tires_res.get("Koszt1KplOpon", 0.0)),
                    "IloscOpon": float(tires_res.get("IloscOpon", 0.0)),
                },
                "trace": tires_res.get("trace", [])
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
                "metadata": {
                    "additional_costs_base": {
                        "source": "LTRSubCalculatorKosztyDodatkowe.py -> calculate_cost()",
                        "formula": "Suma kosztów z tabeli CC (GPS, Zarządzanie, Inne... dzielona przez okres) * narzut (jesli aplikowalne)",
                    },
                    "additional_costs_total": {
                        "source": "PipelineDebugger.py",
                        "formula": "additional_costs_base * months",
                    },
                },
                "trace": add_calc_res.get("trace", []),
            }
        )

        # KROK 3: Samochód Zastępczy (SZst)
        klasa_id = str(self.vehicle.get("samar_class_id", "")) if self.vehicle else ""
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
                "metadata": {
                    "rc_base": {
                        "source": "LTRSubCalculatorSamochodZastepczy.py -> calculate_cost()",
                        "formula": "Stawka miesięczna z bazy (insurance_samochody_zastepcze_kategorie) dla wskazanej klasy pojazdu",
                    },
                    "rc_total": {
                        "source": "PipelineDebugger.py",
                        "formula": "rc_base * months",
                    },
                },
                "trace": rc_res.get("trace", []),
            }
        )

        # KROK 4: Serwis (Srw)
        normatywny_przebieg = getattr(self.settings, "normatywny_przebieg_mc", 1667)
        pakiet_serwisowy_val = float(getattr(self.input_data, "pakiet_serwisowy", 0.0))
        inne_koszty_val = float(
            getattr(self.input_data, "inne_koszty_serwisowania_netto", 0.0)
        )

        service_input = ServiceCalculatorInput(
            z_serwisem=True,
            opcja_serwisowa=self._opcja_serwisowa,
            normatywny_przebieg_mc=normatywny_przebieg,
            samar_class_id=int(self.vehicle.get("samar_class_id", 0))
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
        service_from_new_dict = service_calc.calculate()
        service_from_new = float(service_from_new_dict["monthly_service"])

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
                "metadata": {
                    "service_base": {
                        "source": "LTRSubCalculatorSerwisNew.py -> calculate()",
                        "formula": "Złożony wzór bazujący na przeglądach/częściach silnika zależących od przebiegu/okresu + Pakiet Serwisowy i Inne Koszty",
                    },
                    "service_total": {
                        "source": "PipelineDebugger.py",
                        "formula": "service_base * months",
                    },
                },
                "trace": service_from_new_dict.get("trace", getattr(service_calc, "trace", [])),
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
                "metadata": {
                    "capex_for_financing": {
                        "source": "PipelineDebugger.py",
                        "formula": "Cena Pojazdu Netto (po rabacie) + Opcje Fabryczne + Opcje Serwisowe + Opony CAPEX",
                    }
                },
                "trace": [
                    f"Początkowy bazowy CAPEX (bez zniżek) = {base_price_net_full}",
                    f"Wyliczony vehicle_capex = {vehicle_capex}",
                    f"Opcje capex = {options_capex}",
                    f"Tires capex = {tires_capex}",
                    f"Suma Capex for Financing = {capex_for_financing}",
                ],
            }
        )

        # KROK 6: Utrata Wartości (WR)
        rv_calc = LTRSubCalculatorUtrataWartosciNew(self.vehicle, self.input_data)
        base_wr_options = sum(opt.price_net for opt in self.input_data.factory_options)
        
        # W V1 Utrata Wartości (Amortyzacja) liczona jest WYŁĄCZNIE od ceny pojazdu i opcji fabrycznych (bez opon i bez opcji serwisowych)
        discount_pct = getattr(self.input_data, "discount_pct", 0) / 100.0
        discounted_factory_options = base_wr_options * (1 - discount_pct)
        wp_amortyzacja = vehicle_capex + discounted_factory_options
        
        vat_rate = getattr(self.settings, "vat_rate", 1.23)
        if vat_rate > 10.0:
            vat_rate = 1.0 + (vat_rate / 100.0)

        rv_res = rv_calc.calculate_values(
            months=months,
            total_km=total_km,
            base_vehicle_capex_gross=base_price_net_full * vat_rate,
            options_capex_gross=base_wr_options * vat_rate,
        )

        orig_vr_samar = float(rv_res["WR"])
        orig_utrata_bez_czynszu = wp_amortyzacja - orig_vr_samar
        orig_utrata_z_czynszem = orig_utrata_bez_czynszu  # Legacy V1 parity, no initial rent reduction for technical utrata yet

        vr_samar = float(overrides.get("step_6_wr", orig_vr_samar))

        if "step_6_wr" in overrides:
            utrata_z_czynszem = overrides.get(
                "step_6_utrata_z_czynszem", wp_amortyzacja - vr_samar
            )
            utrata_bez_czynszu = overrides.get(
                "step_6_utrata_bez_czynszu", wp_amortyzacja - vr_samar
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
                    "base_vehicle_capex_gross": base_price_net_full * vat_rate,
                    "options_capex_gross": base_wr_options * vat_rate,
                    "wp_amortyzacja": wp_amortyzacja,
                },
                "outputs": {
                    "vr_samar": vr_samar,
                    "utrata_z_czynszem": utrata_z_czynszem,
                    "utrata_bez_czynszu": utrata_bez_czynszu,
                },
                "metadata": {
                    "utrata_z_czynszem": {
                        "source": "PipelineDebugger.py",
                        "formula": "WP_Amortyzacji (Auto+OpcjeF) - Wartość Końcowa (WR)",
                    },
                },
                "trace": rv_res.get("trace", []),
            }
        )

        # KROK 7: Amortyzacja (Am)
        if getattr(self.input_data, "depreciation_pct", None) is not None:
            orig_procent_amortyzacji_miesiecznie = float(
                self.input_data.depreciation_pct
            )
        else:
            amort_input = AmortyzacjaInput(
                wp_finansowanie=capex_for_financing,
                wp_amortyzacja=wp_amortyzacja,
                wr=vr_samar,
                okres=months,
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
                "metadata": {
                    "procent_amortyzacji_miesiecznie": {
                        "source": "LTRSubCalculatorAmortyzacja.py -> calculate()",
                        "formula": "Różnica % między Wartością Początkową (CAPEX) a Wartością Końcową (WR) podzielona przez Okres",
                    }
                },
                "trace": getattr(amort_result, "trace", getattr(AmortyzacjaCalculator, "trace", [])) if 'amort_result' in locals() else [f"Amortyzacja pobrana sztywno z input_data: {orig_procent_amortyzacji_miesiecznie}%"],
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
                "metadata": {
                    "insurance_base": {
                        "source": "LTRSubCalculatorUbezpieczenie.py -> calculate_cost()",
                        "formula": "Bazuje na stawkach (OC/AC) na przestrzeni 7 lat (korekty amortyzacji) oraz szkodowości (kategoria pojazdu)",
                    },
                    "insurance_total": {
                        "source": "PipelineDebugger.py",
                        "formula": "insurance_base * months",
                    },
                },
                "trace": insurance_res.get("trace", getattr(ins_calc, "trace", [])),
            }
        )

        # KROK 9: Finanse (PMT) (Fi) — V1 parity
        vat_rate_fin = getattr(self.settings, "vat_rate", 1.23)
        if vat_rate_fin > 10.0:
            vat_rate_fin = 1.0 + (vat_rate_fin / 100.0)
        finance_input = FinanseInput(
            WartoscPoczatkowaNetto=capex_for_financing,
            WrPrzewidywanaCenaSprzedazy=vr_samar,
            CzynszInicjalny=float(getattr(self.input_data, "CzynszKwota", 0.0) or 0.0),
            CzynszProcent=float(getattr(self.input_data, "CzynszProcent", 0.0) or 0.0),
            RodzajCzynszu=str(getattr(self.input_data, "RodzajCzynszu", "Kwotowo")),
            StawkaVAT=vat_rate_fin,
            Okres=months,
            WIBORProcent=float(getattr(self.input_data, "wibor_pct", 0.0) or 0.0),
            MarzaFinansowaProcent=float(
                getattr(self.input_data, "margin_pct", 0.0) or 0.0
            ),
        )
        finance_calc = FinanseCalculator(finance_input)
        finance_res = finance_calc.calculate()

        orig_koszt_finansowy = float(finance_res.SumaOdsetekZczynszem)
        orig_czynsz_inicjalny = float(finance_res.CzynszInicjalnyNetto)
        orig_suma_odsetek_bez = float(finance_res.SumaOdsetekBEZczynszu)

        koszt_finansowy = overrides.get("step_9_fi_koszt", orig_koszt_finansowy)
        czynsz_inicjalny = overrides.get("step_9_fi_czynsz", orig_czynsz_inicjalny)
        suma_odsetek_bez = overrides.get("step_9_fi_suma_bez", orig_suma_odsetek_bez)

        steps.append(
            {
                "step": 9,
                "name": "Finanse (PMT)",
                "inputs": vars(finance_input),
                "outputs": {
                    "koszt_finansowy": koszt_finansowy,
                    "suma_odsetek_bez_czynszu": suma_odsetek_bez,
                    "czynsz_inicjalny": czynsz_inicjalny,
                    "monthly_pmt_z_czynszem": float(finance_res.monthly_pmt_z_czynszem),
                    "monthly_pmt_bez_czynszu": float(
                        finance_res.monthly_pmt_bez_czynszu
                    ),
                    "wykup_kwota": float(finance_res.WykupKwota),
                    "czynsz_procent": float(finance_res.CzynszInicjalnyProcent),
                },
                "metadata": {
                    "koszt_finansowy": {
                        "source": "LTRSubCalculatorFinanse.py -> calculate()",
                        "formula": "Suma odsetek Z czynszem — iteracyjny harmonogram V1 (PMT.cs)",
                    },
                    "suma_odsetek_bez_czynszu": {
                        "source": "LTRSubCalculatorFinanse.py -> calculate()",
                        "formula": "Suma odsetek BEZ czynszu — kredyt = pełne WP, ten sam wykup",
                    },
                    "czynsz_inicjalny": {
                        "source": "LTRSubCalculatorFinanse.py -> calculate()",
                        "formula": "CzynszBrutto / VAT (kwotowy) lub WP × % (procentowy)",
                    },
                },
                "trace": getattr(finance_res, "trace", getattr(finance_calc, "trace", [])),
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
            suma_odsetek_bez_czynszu=suma_odsetek_bez,
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
                "metadata": {
                    "koszt_mc": {
                        "source": "LTRSubCalculatorKosztDzienny.py -> calculate()",
                        "formula": "Suma wszystkich kosztów (Utrata + Ubezpieczenie + Koszty Dodatkowe + Opony + Serwis + Zastępczy + Finansowanie) podzielona przez Okres",
                    },
                    "koszty_ogolem": {
                        "source": "LTRSubCalculatorKosztDzienny.py -> calculate()",
                        "formula": "Matematyczna suma wszystkich wydatków ponoszonych w trakcie okresu (przed narzutem marży docelowej)",
                    },
                },
                "trace": getattr(kd_result, "trace", []),
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
                "metadata": {
                    "oferowana_stawka": {
                        "source": "LTRSubCalculatorStawka.py -> calculate()",
                        "formula": "koszt_mc / (1 - marża%) (aplikowanie docelowego uzysku)",
                    },
                    "marza_mc": {
                        "source": "LTRSubCalculatorStawka.py -> calculate()",
                        "formula": "oferowana_stawka - koszt_mc",
                    },
                },
                "trace": getattr(stawka_result, "trace", []),
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
                "metadata": {
                    "korekta_wr_maks": {
                        "source": "LTRSubCalculatorBudzetMarketingowy.py -> calculate()",
                        "formula": "(Oczekiwana wartość WR - WR_SAMAR) / VAT",
                    }
                },
                "trace": getattr(bm_result, "trace", []),
            }
        )

        return steps

    @staticmethod
    def render_steps_html(
        steps: List[Dict[str, Any]],
        months: int,
        vehicle_id: str = "",
    ) -> str:
        """Renderuje kartę HTML z krokami pipeline w formacie porównawczym, z obsługą wejść, precyzyjnych logów (trace) i metadanych."""

        def _fmt_value(value: Any) -> str:
            from decimal import Decimal
            if isinstance(value, (float, Decimal)):
                return f"{value:,.4f}".replace(",", " ")
            if isinstance(value, int):
                return f"{value:,}".replace(",", " ")
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        section_html_parts: List[str] = []
        for step in steps:
            outputs = step.get("outputs") or {}
            inputs = step.get("inputs") or {}
            metadata = step.get("metadata") or {}
            trace = step.get("trace") or []

            output_rows = "".join(
                f"<tr><td>{escape(str(k))}</td><td class='val'>{escape(_fmt_value(v))}</td></tr>"
                for k, v in outputs.items()
            )
            input_rows = "".join(
                f"<tr><td>{escape(str(k))}</td><td class='val'>{escape(_fmt_value(v))}</td></tr>"
                for k, v in inputs.items()
            )
            metadata_rows = "".join(
                f"<tr><td>{escape(str(k))}</td><td class='val'>{escape(_fmt_value(v))}</td></tr>"
                for k, v in metadata.items()
            )

            trace_html = ""
            if trace:
                trace_items = "".join(f"<li>{escape(str(t))}</li>" for t in trace)
                trace_html = f"<div class='trace-box'><h4>Ślad rewizyjny (Trace)</h4><ul class='trace-list'>{trace_items}</ul></div>"

            section_html_parts.append(
                f"<section class='sec'>"
                f"<h3>Krok {escape(str(step.get('step', '?')))}: {escape(str(step.get('name', '')))}</h3>"
                f"<div class='columns'>"
                f"  <div class='col main-col'>"
                f"    <h4>Wyniki (Outputs)</h4>"
                f"    <table>"
                f"      <thead><tr><th>Parametr</th><th>Wartość</th></tr></thead>"
                f"      <tbody>{output_rows}</tbody>"
                f"    </table>"
                f"  </div>"
                f"  <div class='col side-col'>"
                f"    <details><summary>Wejścia (Inputs)</summary>"
                f"      <table><tbody>{input_rows}</tbody></table>"
                f"    </details>"
                f"    <details><summary>Zasady (Metadata)</summary>"
                f"      <table><tbody>{metadata_rows}</tbody></table>"
                f"    </details>"
                f"  </div>"
                f"</div>"
                f"{trace_html}"
                f"</section>"
            )

        title = "Pipeline Debugger - Pełny Ślad Rewizyjny (Calculation Trace)"
        sub = f"Pojazd: {vehicle_id} | Okres: {months} mc"

        return (
            "<!doctype html><html><head><meta charset='utf-8'/>"
            "<style>"
            "body{font-family:Segoe UI,Tahoma,Geneva,Verdana,sans-serif;background:#f1f5f9;color:#0f172a;margin:20px;}"
            "h1{font-size:20px;margin:0 0 4px 0;color:#1e293b;}"
            "p.meta{margin:0 0 20px 0;color:#475569;font-size:13px;}"
            "section.sec{margin:0 0 16px 0;padding:16px;border:1px solid #cbd5e1;border-radius:10px;background:#ffffff;box-shadow: 0 1px 3px rgba(0,0,0,0.05);}"
            "h3{margin:0 0 12px 0;font-size:16px;color:#0f172a;border-bottom: 2px solid #e2e8f0;padding-bottom: 6px;}"
            "h4{margin:0 0 8px 0;font-size:13px;color:#334155;}"
            ".columns{display:flex;gap:16px;margin-bottom:12px;}"
            ".col{flex:1;}"
            ".main-col{flex:1.5;}"
            ".side-col{flex:1;}"
            "details{margin-bottom:8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:4px 8px;}"
            "summary{font-weight:600;font-size:13px;cursor:pointer;color:#3b82f6;}"
            "summary:hover{color:#2563eb;}"
            "table{width:100%;border-collapse:collapse;font-size:12px;background:#fff;margin-top:6px;}"
            "th,td{border:1px solid #e2e8f0;padding:6px 8px;text-align:left;vertical-align:top;}"
            "th{background:#f8fafc;color:#475569;font-weight:600;}"
            "td.val{text-align:right;font-weight:600;white-space:nowrap;color:#0f172a;}"
            ".trace-box{margin-top:12px;padding:10px;background:#1e293b;border-radius:6px;color:#f8fafc;font-family:Consolas,monospace;font-size:12px;}"
            ".trace-box h4{color:#94a3b8;margin:0 0 6px 0;text-transform:uppercase;font-size:11px;}"
            ".trace-list{margin:0;padding-left:16px;}"
            ".trace-list li{margin-bottom:4px;}"
            "</style></head><body>"
            f"<h1>{escape(title)}</h1>"
            f"<p class='meta'>{escape(sub)}</p>"
            + "".join(section_html_parts)
            + "</body></html>"
        )
