"""
diagnose_calculators.py – Diagnostyka Pipeline Kalkulacyjnego

Uruchamia KAŻDY z 12 sub-kalkulatorów krok po kroku (w kolejności V1)
i wypisuje ✅ OK / ❌ FAIL z wartością wynikową lub komunikatem błędu.

Kolejność V1 (LTRKalkulator.cs linie 250-398):
  1. (Op)   Opony
  2. (KDod) Koszty Dodatkowe
  3. (SZst) Samochód Zastępczy
  4. (Srw)  Serwis
  5. (CeZ)  Cena Zakupu (CAPEX)
  6. (UtW)  Utrata Wartości (WR)
  7. (Am)   Amortyzacja
  8. (Ub)   Ubezpieczenie
  9. (Fi)   Finanse (PMT)
 10. (KDz)  Koszt Dzienny
 11. (St)   Stawka
 12. (Bm)   Budżet Marketingowy

Użycie:
    cd d:\\kalk_v3\\backend
    python scripts/diagnose_calculators.py                  # wszystkie pojazdy
    python scripts/diagnose_calculators.py <vehicle_id>     # jeden pojazd
"""

import sys
import os
import traceback
from typing import Any, Dict, List, cast

# Dodaj backend do PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.database import supabase
from core.models import ControlCenterSettings


# ── Stałe diagnostyczne ──
MONTHS = 48
PRZEBIEG_BAZOWY = 140_000
KM_PER_MONTH = PRZEBIEG_BAZOWY / MONTHS
TOTAL_KM = int(KM_PER_MONTH * MONTHS)

# Kolorowe oznaczenia dla terminala
OK = "✅"
FAIL = "❌"
WARN = "⚠️"
SEP = "─" * 70


def load_settings() -> ControlCenterSettings:
    """Pobiera ControlCenterSettings z control_center (id=1)."""
    res = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not res.data:
        raise RuntimeError("Brak ustawień control_center (id=1)!")
    return ControlCenterSettings(**cast(Dict[str, Any], res.data[0]))


def load_vehicles(vehicle_id: str | None = None) -> List[Dict[str, Any]]:
    """Pobiera pojazdy do diagnostyki."""
    query = supabase.table("vehicle_synthesis").select("*")
    if vehicle_id:
        query = query.eq("id", vehicle_id)
    res = query.execute()
    if not res.data:
        raise RuntimeError(
            f"Brak pojazdów w pojazdy_master"
            f"{f' (id={vehicle_id})' if vehicle_id else ''}!"
        )
    return cast(List[Dict[str, Any]], res.data)


def build_mock_input(vehicle: Dict[str, Any], settings: ControlCenterSettings) -> Any:
    """Buduje CalculatorInput z domyślnymi wartościami."""
    # Import tutaj żeby sys.path działał
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from main import CalculatorInput

    return CalculatorInput(
        vehicle_id=str(vehicle.get("id", "")),
        base_price_net=float(vehicle.get("base_price_net", 100_000)),
        discount_pct=0.0,
        factory_options=[],
        service_options=[],
        okres_bazowy=MONTHS,
        przebieg_bazowy=PRZEBIEG_BAZOWY,
        pricing_margin_pct=15.0,
        wibor_pct=5.0,
        margin_pct=2.0,
        z_oponami=True,
        klasa_opony_string="Medium",
        srednica_felgi=int(vehicle.get("rim_size", 17) or 17),
        replacement_car_enabled=True,
    )


def step_header(num: int, code: str, name: str) -> str:
    return f"  Krok {num:>2} ({code:>4}) {name}"


def diagnose_vehicle(
    vehicle: Dict[str, Any],
    settings: ControlCenterSettings,
) -> Dict[str, str]:
    """Uruchamia 12 sub-kalkulatorów dla jednego pojazdu. Zwraca raport."""
    vid = vehicle.get("id", "?")
    brand = vehicle.get("brand", "?")
    model = vehicle.get("model", "?")
    klasa_id = str(vehicle.get("klasa_wr_id", "") or "")

    print(f"\n{SEP}")
    print(f"  POJAZD: {brand} {model}  (id={vid}, klasa_wr={klasa_id})")
    print(f"  Wariant: {MONTHS}mc / {TOTAL_KM:,} km")
    print(SEP)

    calc_input = build_mock_input(vehicle, settings)
    results: Dict[str, str] = {}

    # Zmienne przekazywane między krokami
    tires_res: Dict[str, Any] = {}
    capex: float = 0.0
    vehicle_capex: float = 0.0
    options_capex: float = 0.0
    capex_for_financing: float = 0.0
    add_costs_total: float = 0.0
    rc_total: float = 0.0
    service_total: float = 0.0
    tires_total: float = 0.0
    insurance_total: float = 0.0
    vr_samar: float = 0.0
    utrata_z_czynszem: float = 0.0
    utrata_bez_czynszu: float = 0.0
    procent_amortyzacji: float = 0.0
    finance_total_interest: float = 0.0
    finance_initial_deposit: float = 0.0
    service_base: float = 0.0

    # ── KROK 1: OPONY ──
    try:
        from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony

        tires_calc = LTRSubCalculatorOpony(
            z_oponami=True,
            klasa_opony_string="Medium",
            srednica_felgi=int(vehicle.get("rim_size", 17) or 17),
        )
        tires_res = tires_calc.calculate_cost(months=MONTHS, total_km=TOTAL_KM)
        tires_total = (
            float(
                tires_res["monthly_hardware"]
                + tires_res["monthly_storage"]
                + tires_res["monthly_swaps"]
            )
            * MONTHS
        )
        msg = (
            f"capex_initial={tires_res['capex_initial_set']:.2f}, "
            f"mc_total={tires_res['monthly_hardware'] + tires_res['monthly_storage'] + tires_res['monthly_swaps']:.2f}"
        )
        print(f"  {OK}  {step_header(1, 'Op', 'Opony')} → {msg}")
        results["1_Opony"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(1, 'Op', 'Opony')} → {e}")
        results["1_Opony"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 2: KOSZTY DODATKOWE ──
    try:
        from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator

        add_calc = AdditionalCostsCalculator(settings, calc_input, MONTHS)
        add_res = add_calc.calculate_cost()
        add_costs_total = float(add_res["monthly_additional_costs"]) * MONTHS
        msg = (
            f"mc={add_res['monthly_additional_costs']:.2f}, total={add_costs_total:.2f}"
        )
        print(f"  {OK}  {step_header(2, 'KDod', 'Koszty Dodatkowe')} → {msg}")
        results["2_KosztyDodatkowe"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(2, 'KDod', 'Koszty Dodatkowe')} → {e}")
        results["2_KosztyDodatkowe"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 3: SAMOCHÓD ZASTĘPCZY ──
    try:
        from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
        from core.LTRKalkulator import get_replacement_car_rate_from_db

        rc_rate = get_replacement_car_rate_from_db(klasa_id)
        rc_calc = ReplacementCarCalculator(rc_rate)
        rc_res = rc_calc.calculate_cost(months=MONTHS, enabled=True)
        rc_total = float(rc_res.get("total_replacement_car", 0.0))
        msg = f"mc={rc_res['monthly_replacement_car']:.2f}, total={rc_total:.2f}"
        print(f"  {OK}  {step_header(3, 'SZst', 'Samochód Zastępczy')} → {msg}")
        results["3_SamochodZastepczy"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(3, 'SZst', 'Samochód Zastępczy')} → {e}")
        results["3_SamochodZastepczy"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 4: SERWIS ──
    try:
        from core.LTRSubCalculatorSerwisNew import (
            ServiceCalculator,
            ServiceCalculatorInput,
        )

        service_input = ServiceCalculatorInput(
            z_serwisem=True,
            opcja_serwisowa="ASO",
            normatywny_przebieg_mc=getattr(settings, "normatywny_przebieg_mc", 1667),
            samar_class_id=int(vehicle.get("klasa_wr_id", 0) or 0),
            engine_type_id=int(vehicle.get("engine_type_id", 1) or 1),
            power_kw=float(vehicle.get("power_kw", 100) or 100),
            przebieg=TOTAL_KM,
            okres=MONTHS,
        )
        service_calc = ServiceCalculator(service_input)
        service_base = service_calc.calculate()
        service_total = service_base * MONTHS
        msg = f"mc={service_base:.2f}, total={service_total:.2f}"
        print(f"  {OK}  {step_header(4, 'Srw', 'Serwis')} → {msg}")
        results["4_Serwis"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(4, 'Srw', 'Serwis')} → {e}")
        results["4_Serwis"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 5: CENA ZAKUPU (CAPEX) ──
    try:
        from core.LTRSubCalculatorCenaZakupu import (
            PurchasePriceCalculator,
            PurchasePriceInput,
        )

        gsm_cost = settings.cost_gsm_device + settings.cost_gsm_installation
        pp_input = PurchasePriceInput(
            base_price_net=float(vehicle.get("base_price_net", 100_000)),
            options=[],
            discount_pct=0.0,
            add_gsm_device=True,
            gsm_hardware_cost=gsm_cost,
        )
        pp_calc = PurchasePriceCalculator(pp_input)
        pp_res = pp_calc.calculate()
        vehicle_capex = pp_res.discounted_base
        options_capex = pp_res.total_options_capex
        capex = vehicle_capex + options_capex
        capex_for_financing = capex + float(tires_res.get("capex_initial_set", 0))
        msg = (
            f"vehicle_capex={vehicle_capex:.2f}, "
            f"options_capex={options_capex:.2f}, "
            f"capex_total={capex_for_financing:.2f}"
        )
        print(f"  {OK}  {step_header(5, 'CeZ', 'Cena Zakupu (CAPEX)')} → {msg}")
        results["5_CenaZakupu"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(5, 'CeZ', 'Cena Zakupu (CAPEX)')} → {e}")
        results["5_CenaZakupu"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 6: UTRATA WARTOŚCI (WR) ──
    try:
        from core.LTRSubCalculatorUtrataWartosciNew import (
            LTRSubCalculatorUtrataWartosciNew,
        )

        vat_rate = getattr(settings, "vat_rate", 1.23)
        if vat_rate > 10.0:
            vat_rate = 1.0 + (vat_rate / 100.0)

        rv_calc = LTRSubCalculatorUtrataWartosciNew(vehicle, calc_input)
        rv_res = rv_calc.calculate_values(
            months=MONTHS,
            total_km=TOTAL_KM,
            base_vehicle_capex_gross=vehicle_capex * vat_rate,
            options_capex_gross=float(tires_res.get("capex_initial_set", 0)) * vat_rate,
        )
        vr_samar = rv_res["WR"]
        utrata_z_czynszem = float(
            rv_res.get(
                "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - vr_samar
            )
        )
        utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])
        msg = (
            f"WR_net={vr_samar:.2f}, "
            f"WR_gross={rv_res['WR_Gross']:.2f}, "
            f"UtrataBEZcz={utrata_bez_czynszu:.2f}"
        )
        print(f"  {OK}  {step_header(6, 'UtW', 'Utrata Wartości (WR)')} → {msg}")
        results["6_UtrataWartosci"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(6, 'UtW', 'Utrata Wartości (WR)')} → {e}")
        results["6_UtrataWartosci"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 7: AMORTYZACJA ──
    try:
        from core.LTRSubCalculatorAmortyzacja import (
            AmortyzacjaCalculator,
            AmortyzacjaInput,
        )

        amort_input = AmortyzacjaInput(
            wp=capex_for_financing, wr=vr_samar, okres=MONTHS
        )
        amort_res = AmortyzacjaCalculator(amort_input).calculate()
        procent_amortyzacji = amort_res.amortyzacja_procent
        msg = (
            f"amort%={procent_amortyzacji:.6f}, "
            f"utrata={amort_res.utrata_wartosci:.2f}, "
            f"kwota_1mc={amort_res.kwota_amortyzacji_1_miesiac:.2f}"
        )
        print(f"  {OK}  {step_header(7, 'Am', 'Amortyzacja')} → {msg}")
        results["7_Amortyzacja"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(7, 'Am', 'Amortyzacja')} → {e}")
        results["7_Amortyzacja"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 8: UBEZPIECZENIE ──
    try:
        from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
        from core.LTRKalkulator import (
            get_insurance_rates_from_db,
            get_damage_coefficients_from_db,
        )

        insurance_rates = get_insurance_rates_from_db(klasa_id)
        damage_coeffs = get_damage_coefficients_from_db(klasa_id)

        # build_matrix wywołuje InsuranceCalculator z tymi kwargs:
        ins_calc = InsuranceCalculator(
            insurance_rates=insurance_rates,
            damage_coefficients=damage_coeffs,
            settings=settings,
            amortization_pct=procent_amortyzacji,
            total_km=TOTAL_KM,
        )
        insurance_res = ins_calc.calculate_cost(MONTHS, capex_for_financing)
        insurance_total = float(insurance_res.get("total_insurance", 0.0))
        msg = (
            f"mc={insurance_res['monthly_insurance']:.2f}, total={insurance_total:.2f}"
        )
        print(f"  {OK}  {step_header(8, 'Ub', 'Ubezpieczenie')} → {msg}")
        results["8_Ubezpieczenie"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(8, 'Ub', 'Ubezpieczenie')} → {e}")
        results["8_Ubezpieczenie"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 9: FINANSE (PMT) ──
    try:
        from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput

        vat_rate_diag = getattr(settings, "vat_rate", 1.23)
        if vat_rate_diag > 10.0:
            vat_rate_diag = 1.0 + (vat_rate_diag / 100.0)

        finance_input = FinanseInput(
            WartoscPoczatkowaNetto=capex_for_financing,
            WrPrzewidywanaCenaSprzedazy=vr_samar,
            CzynszInicjalny=0.0,
            CzynszProcent=0.0,
            RodzajCzynszu="Kwotowo",
            StawkaVAT=vat_rate_diag,
            Okres=MONTHS,
            WIBORProcent=5.0,
            MarzaFinansowaProcent=2.0,
        )
        finance_calc = FinanseCalculator(finance_input)
        finance_res = finance_calc.calculate()
        finance_total_interest = finance_res.SumaOdsetekZczynszem
        finance_initial_deposit = finance_res.CzynszInicjalnyNetto
        msg = (
            f"PMT_z_cz={finance_res.monthly_pmt_z_czynszem:.2f}, "
            f"odsetki_z={finance_res.SumaOdsetekZczynszem:.2f}, "
            f"odsetki_bez={finance_res.SumaOdsetekBEZczynszu:.2f}"
        )
        print(f"  {OK}  {step_header(9, 'Fi', 'Finanse (PMT)')} → {msg}")
        results["9_Finanse"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(9, 'Fi', 'Finanse (PMT)')} → {e}")
        results["9_Finanse"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 10: KOSZT DZIENNY ──
    try:
        from core.LTRSubCalculatorKosztDzienny import (
            KosztDziennyCalculator,
            KosztDziennyInput,
        )

        kd_input = KosztDziennyInput(
            utrata_wartosci_z_czynszem=utrata_z_czynszem,
            utrata_wartosci_bez_czynszu=utrata_bez_czynszu,
            koszt_finansowy=finance_total_interest,
            samochod_zastepczy_netto=rc_total,
            koszty_dodatkowe_netto=add_costs_total,
            ubezpieczenie_netto=insurance_total,
            opony_netto=tires_total,
            serwis_netto=service_total,
            suma_odsetek_bez_czynszu=finance_total_interest,
            okres=MONTHS,
        )
        kd_res = KosztDziennyCalculator(kd_input).calculate()
        msg = (
            f"koszt_dzienny={kd_res.koszt_dzienny:.2f}, "
            f"koszt_mc={kd_res.koszt_mc:.2f}, "
            f"koszty_ogolem={kd_res.koszty_ogolem:.2f}"
        )
        print(f"  {OK}  {step_header(10, 'KDz', 'Koszt Dzienny')} → {msg}")
        results["10_KosztDzienny"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(10, 'KDz', 'Koszt Dzienny')} → {e}")
        results["10_KosztDzienny"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 11: STAWKA ──
    try:
        from core.LTRSubCalculatorStawka import StawkaCalculator, StawkaInput

        margin_pct = 15.0 / 100.0

        stawka_input = StawkaInput(
            koszt_mc=kd_res.koszt_mc,
            koszt_mc_bez_czynszu=kd_res.koszt_mc_bez_czynszu,
            utrata_wartosci_netto=utrata_z_czynszem,
            koszty_finansowe_netto=finance_total_interest,
            ubezpieczenie_netto=insurance_total,
            samochod_zastepczy_netto=rc_total,
            koszty_dodatkowe_netto=add_costs_total,
            opony_netto=tires_total,
            serwis_netto=service_total,
            okres=MONTHS,
            marza=margin_pct,
            czynsz_inicjalny=finance_initial_deposit,
        )
        stawka_res = StawkaCalculator(stawka_input).calculate()
        msg = (
            f"stawka_mc={stawka_res.oferowana_stawka:.2f}, "
            f"marza_mc={stawka_res.marza_mc:.2f}, "
            f"cz_fin={stawka_res.czynsz_finansowy:.2f}, "
            f"cz_tech={stawka_res.czynsz_techniczny:.2f}"
        )
        print(f"  {OK}  {step_header(11, 'St', 'Stawka')} → {msg}")
        results["11_Stawka"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(11, 'St', 'Stawka')} → {e}")
        results["11_Stawka"] = f"FAIL: {e}"
        traceback.print_exc()

    # ── KROK 12: BUDŻET MARKETINGOWY ──
    try:
        from core.LTRSubCalculatorBudzetMarketingowy import (
            BudzetMarketingowyCalculator,
            BudzetMarketingowyInput,
        )

        vat_mult = getattr(settings, "vat_rate", 1.23)
        if vat_mult > 10.0:
            vat_mult = 1.0 + (vat_mult / 100.0)
        budzet_ltr = getattr(settings, "budzet_marketingowy_ltr", 0.0)

        bm_input = BudzetMarketingowyInput(
            wr_przewidywana_cena_sprzedazy=vr_samar,
            stawka_vat=vat_mult,
            budzet_marketingowy_ltr=budzet_ltr,
        )
        bm_res = BudzetMarketingowyCalculator(bm_input).calculate()
        msg = f"korekta_wr_maks={bm_res.korekta_wr_maks:.2f}"
        print(f"  {OK}  {step_header(12, 'Bm', 'Budżet Marketingowy')} → {msg}")
        results["12_BudzetMarketingowy"] = f"OK: {msg}"
    except Exception as e:
        print(f"  {FAIL}  {step_header(12, 'Bm', 'Budżet Marketingowy')} → {e}")
        results["12_BudzetMarketingowy"] = f"FAIL: {e}"
        traceback.print_exc()

    return results


def main() -> None:
    """Punkt wejścia skryptu diagnostycznego."""
    print("\n" + "═" * 70)
    print("  DIAGNOSTYKA PIPELINE KALKULACYJNEGO (V1 order)")
    print("  Wariant referencyjny: 48mc / 140 000 km")
    print("═" * 70)

    # 1. Załaduj ustawienia CC
    try:
        settings = load_settings()
        print(f"\n  {OK} Załadowano ControlCenterSettings (VAT={settings.vat_rate})")
    except Exception as e:
        print(f"\n  {FAIL} Nie można załadować ustawień: {e}")
        return

    # 2. Załaduj pojazdy
    vehicle_id = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        vehicles = load_vehicles(vehicle_id)
        print(f"  {OK} Znaleziono {len(vehicles)} pojazd(ów)")
    except Exception as e:
        print(f"  {FAIL} Nie można załadować pojazdów: {e}")
        return

    # 3. Uruchom diagnostykę
    all_results: Dict[str, Dict[str, str]] = {}
    for v in vehicles:
        vid = v.get("id", "?")
        res = diagnose_vehicle(v, settings)
        all_results[str(vid)] = res

    # 4. Podsumowanie
    print(f"\n{'═' * 70}")
    print("  PODSUMOWANIE")
    print("═" * 70)

    for vid, res in all_results.items():
        ok_count = sum(1 for v in res.values() if v.startswith("OK"))
        fail_count = sum(1 for v in res.values() if v.startswith("FAIL"))
        total = len(res)
        status = OK if fail_count == 0 else FAIL
        print(f"  {status} Pojazd {vid}: {ok_count}/{total} OK, {fail_count} FAIL")

        if fail_count > 0:
            for step_name, step_res in res.items():
                if step_res.startswith("FAIL"):
                    print(f"      {FAIL} {step_name}: {step_res}")

    failed_vehicles = sum(
        1
        for res in all_results.values()
        if any(v.startswith("FAIL") for v in res.values())
    )
    total_vehicles = len(all_results)
    print(
        f"\n  Łącznie: {total_vehicles - failed_vehicles}/{total_vehicles} pojazdów OK"
    )
    print("═" * 70 + "\n")


if __name__ == "__main__":
    main()
