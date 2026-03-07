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

        vehicle_capex, options_capex = self._calculate_capex()
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
                "metadata": {
                    "tires_base": {
                        "source": "LTRSubCalculatorOpony.py -> calculate_cost()",
                        "formula": "Suma: sprzęt (opony/felgi) + raty za przechowywanie + raty za wymiany (uzależnione od 'Z Oponami' oraz średnicy felgi)",
                    },
                    "tires_capex": {
                        "source": "LTRSubCalculatorOpony.py -> calculate_cost()",
                        "formula": "Jednorazowy koszt początkowego kompletu opon zimowych (wliczony w CAPEX tylko jeśli okres >= 24 msc lub przebieg >= 45k km)",
                    },
                    "tires_total": {
                        "source": "PipelineDebugger.py",
                        "formula": "tires_base * months",
                    },
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

        # V1 parity: WR depreciation curve uses full catalogue prices
        # (no discount) to simulate market-rate value loss.
        # base_wr_options already uses pre-discount option prices (line 251).
        rv_res = rv_calc.calculate_values(
            months=months,
            total_km=total_km,
            base_vehicle_capex_gross=base_price_net_full * vat_rate,
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
                    "base_vehicle_capex_gross": base_price_net_full * vat_rate,
                    "options_capex_gross": (base_wr_options + tires_capex) * vat_rate,
                },
                "outputs": {
                    "vr_samar": vr_samar,
                    "utrata_z_czynszem": utrata_z_czynszem,
                    "utrata_bez_czynszu": utrata_bez_czynszu,
                    "rv_lo_net": rv_res["WRdlaLO"],
                },
                "metadata": {
                    "vr_samar": {
                        "source": "LTRSubCalculatorUtrataWartosciNew.py -> calculate_values()",
                        "formula": "Wyliczenie tabelaryczne rezydualnej wg cennika SAMAR (z uwzględnieniem przebiegu i wieku po X miesiącach)",
                    },
                    "utrata_z_czynszem": {
                        "source": "LTRSubCalculatorUtrataWartosciNew.py lub PipelineDebugger.py",
                        "formula": "CAPEX łączny (z oponami itp.) mniejszy o Szacowaną Wartość Końcową (vr_samar)",
                    },
                    "utrata_bez_czynszu": {
                        "source": "PipelineDebugger.py",
                        "formula": "Tożsame z utrata_z_czynszem; legacy placeholder",
                    },
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
                "metadata": {
                    "procent_amortyzacji_miesiecznie": {
                        "source": "LTRSubCalculatorAmortyzacja.py -> calculate()",
                        "formula": "Różnica % między Wartością Początkową (CAPEX) a Wartością Końcową (WR) podzielona przez Okres",
                    }
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
            }
        )

        return steps
