"""Diagnostyka V3 vs V1 — Skoda Superb 24mc / 140k / rabat 24% / marza 15%"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import core.LTRKalkulator as ltr_mod
ltr_mod.get_vehicle_from_db.cache_clear()
ltr_mod.get_samar_klasa_from_db.cache_clear()
ltr_mod.get_insurance_rates_from_db.cache_clear()
ltr_mod.get_replacement_car_rate_from_db.cache_clear()
ltr_mod.get_damage_coefficients_from_db.cache_clear()

from core.database import supabase

# ---- 0. Find Skoda Superb ----
print("=" * 80)
print("KROK 0: Szukanie pojazdu Skoda Superb")
print("=" * 80)
res = supabase.table("vehicle_synthesis").select(
    "id, brand, model, synthesis_data, zabudowa_apr_wr"
).ilike("model", "%superb%").execute()

if not res.data:
    print("BRAK SUPERBA W BAZIE!")
    sys.exit(1)

for v in res.data:
    sd = v.get("synthesis_data") or {}
    cs = sd.get("card_summary") or {}
    print(f"  ID: {v['id']}")
    print(f"  Brand: {v.get('brand')}, Model: {v.get('model')}")
    print(f"  SAMAR: {cs.get('samar_category', '?')}")
    print(f"  Engine: {cs.get('engine_category', '?')}")
    print(f"  Power kW: {cs.get('power_kw', '?')}")
    print()

# Use the diesel Combi Superb (V1 model: SKODA Superb 2,0 TDI ON 4x4 AT)
vid = None
for v in res.data:
    sd = v.get("synthesis_data") or {}
    cs = sd.get("card_summary") or {}
    eng = cs.get("engine_category", "")
    model_name = v.get("model", "")
    if "diesel" in eng.lower() or "on" in eng.lower() or "combi" in model_name.lower():
        vid = v["id"]
        break
if not vid:
    vid = res.data[0]["id"]
    print("  WARNING: No diesel Combi found, using first match")
print(f"Uzywam vehicle_id = {vid}")

# ---- 1. Vehicle data ----
vehicle = ltr_mod.get_vehicle_from_db(vid)
print("\n" + "=" * 80)
print("KROK 1: Dane pojazdu z DB")
print("=" * 80)
for k, val in vehicle.items():
    print(f"  {k}: {val}")

samar_id = str(vehicle.get("samar_class_id", ""))
print(f"\n  samar_class_id: {samar_id}")

samar_klasa = ltr_mod.get_samar_klasa_from_db(samar_id)
print(f"  samar_klasa_wr: {samar_klasa}")

insurance_rates = ltr_mod.get_insurance_rates_from_db(samar_id)
print(f"  Insurance rates count: {len(insurance_rates)}")
for r in insurance_rates[:7]:
    print(f"    Year {r.get('year')}: AC={r.get('stawka_ac')}, OC={r.get('stawka_oc')}")

damage_coeffs = ltr_mod.get_damage_coefficients_from_db(samar_id)
print(f"  Damage coeffs: {damage_coeffs}")

rc_rate = ltr_mod.get_replacement_car_rate_from_db(samar_id)
print(f"  Replacement car rate: {rc_rate}")

# ---- 2. Calculation params ----
MONTHS = 48  # V1 screenshot: OkresUzytkowania=48
TOTAL_KM = 140000  # V1 screenshot: Przebieg=140000
KM_PER_YEAR = (TOTAL_KM / MONTHS) * 12
CENA_CENNIKOWA = 172642.28  # NETTO (brutto 212350 / 1.23)
OPCJE_FABRYCZNE = 23536.59  # NETTO (brutto 28950 / 1.23)
RABAT_PCT = 23  # V1 screenshot: Rabat=0.2300
MARZA_PCT = 0.15  # V1 screenshot: Marza=0.1500
VAT_RATE = 1.23
ROZMIAR_OPON = 17
KLASA_OPON = "MEDIUM"

print(f"\n  km_per_year: {KM_PER_YEAR}")

# ---- 2a. CAPEX ----
from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator, PurchasePriceInput, PurchasePriceOption,
)

pp_input = PurchasePriceInput(
    base_price_net=CENA_CENNIKOWA,
    options=[
        PurchasePriceOption(
            price_net=OPCJE_FABRYCZNE, name="Opcje", is_service=False, is_discountable=True
        )
    ],
    discount_pct=RABAT_PCT,
    add_gsm_to_capex=True,
    gsm_device_cost_net=469.0,
    gsm_installation_cost_net=150.0,
    pakiet_serwisowy_net=0.0,
)
pp_res = PurchasePriceCalculator(pp_input).calculate()
capex = pp_res.total_capex

print(f"\n{'='*80}")
print("KROK 2: SUB-KALKULATORY")
print(f"{'='*80}")
print("\n  CAPEX:")
print(f"    discounted_base: {pp_res.discounted_base:.2f}")
print(f"    total_capex: {capex:.2f}")
print(f"    tires_capex: {pp_res.tires_capex_net:.2f}")
print(f"    gsm_capex: {pp_res.gsm_capex_net:.2f}")
print(f"    transport: {pp_res.transport_fee_net:.2f}")
print("    V1 Cena zakupu = 154278.97")  # from screenshot

# ---- 2b. OPONY ----
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony

tires_calc = LTRSubCalculatorOpony(
    z_oponami=True,
    klasa_opony_string=KLASA_OPON,
    srednica_felgi=ROZMIAR_OPON,
    korekta_kosztu=False,
    koszt_opon_korekta=0.0,
    sets_needed_override=None,
)
tires_res = tires_calc.calculate_cost(months=MONTHS, total_km=TOTAL_KM)
tires_base = (
    tires_res["monthly_hardware"]
    + tires_res["monthly_storage"]
    + tires_res["monthly_swaps"]
)
tires_total = tires_base * MONTHS

print("\n  OPONY:")
for k, v in tires_res.items():
    print(f"    {k}: {v}")
print(f"    tires_base_mc: {tires_base:.2f}")
print(f"    tires_total: {tires_total:.2f}")
print("    V1 opony mc (z marza) = 220")

capex_for_financing = capex + tires_res["capex_initial_set"]
print(f"\n  capex_for_financing: {capex_for_financing:.2f}")

# ---- 2c. WR / UTRATA WARTOSCI ----
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew

class MockInput:
    korekta_wr = 0.0
    base_price_net = CENA_CENNIKOWA  # netto
    factory_options = []
    service_options = []

rv_calc = LTRSubCalculatorUtrataWartosciNew(vehicle, MockInput())

base_wr_options = OPCJE_FABRYCZNE
rv_res = rv_calc.calculate_values(
    months=MONTHS,
    total_km=TOTAL_KM,
    base_vehicle_capex_gross=CENA_CENNIKOWA * VAT_RATE,
    options_capex_gross=(base_wr_options + tires_res["capex_initial_set"]) * VAT_RATE,
)
vr_samar = rv_res["WR"]
utrata_z_czynszem = rv_res.get(
    "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - vr_samar
)
utrata_bez_czynszu = rv_res["UtrataWartosciBEZczynszu"]

print("\n  UTRATA WARTOSCI:")
print(f"    WR: {vr_samar:.2f}")
print(f"    WRdlaLO: {rv_res['WRdlaLO']:.2f}")
print(f"    UtrataZCzynszem: {utrata_z_czynszem:.2f}")
print(f"    UtrataBEZczynszu: {utrata_bez_czynszu:.2f}")

# ---- 2d. FINANSE ----
from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput

finance_input = FinanseInput(
    WartoscPoczatkowaNetto=capex_for_financing,
    WrPrzewidywanaCenaSprzedazy=vr_samar,
    CzynszInicjalny=0.0,
    CzynszProcent=0.0,
    RodzajCzynszu="Kwotowo",
    StawkaVAT=VAT_RATE,
    Okres=MONTHS,
    WIBORProcent=4.82,  # Per user: control_center WIBOR = 4.82%
    MarzaFinansowaProcent=2.0,  # Default from control_center
)
finance_res = FinanseCalculator(finance_input).calculate()

print("\n  FINANSE:")
print(f"    PMT z czynszem: {finance_res.monthly_pmt_z_czynszem:.2f}")
print(f"    PMT bez czynszu: {finance_res.monthly_pmt_bez_czynszu:.2f}")
print(f"    SumaOdsetekZczynszem: {finance_res.SumaOdsetekZczynszem:.2f}")
print(f"    SumaOdsetekBEZczynszu: {finance_res.SumaOdsetekBEZczynszu:.2f}")
print(f"    CzynszInicjalnyNetto: {finance_res.CzynszInicjalnyNetto:.2f}")
print(f"    WykupKwota: {finance_res.WykupKwota:.2f}")

# ---- 2e. AMORTYZACJA ----
from core.LTRSubCalculatorAmortyzacja import AmortyzacjaCalculator, AmortyzacjaInput

amort_res = AmortyzacjaCalculator(
    AmortyzacjaInput(wp=capex_for_financing, wr=vr_samar, okres=MONTHS)
).calculate()

print("\n  AMORTYZACJA:")
print(f"    procent: {amort_res.amortyzacja_procent:.6f}")

# ---- 2f. UBEZPIECZENIE ----
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator

class MockSettings:
    vat_rate = VAT_RATE
    cost_registration = 233.50
    cost_sales_prep = 800.0
    cost_gsm_monthly = 2.50
    cost_gsm_device = 971.25
    cost_gsm_installation = 0.0
    cost_gsm_subscription_monthly = 2.50
    cost_hook_installation = 80.0
    cost_grid_dismantling = 0.0
    normatywny_przebieg_mc = 1667
    budzet_marketingowy_ltr = 0.0

settings = MockSettings()

ins_calc = InsuranceCalculator(
    insurance_rates=insurance_rates,
    damage_coefficients=damage_coeffs,
    settings=settings,
    amortization_pct=amort_res.amortyzacja_procent,
    total_km=TOTAL_KM,
)
insurance_res = ins_calc.calculate_cost(MONTHS, capex_for_financing)
insurance_base = float(insurance_res["monthly_insurance"])
insurance_total = float(insurance_res.get("total_insurance", insurance_base * MONTHS))

print("\n  UBEZPIECZENIE:")
for k, v in insurance_res.items():
    print(f"    {k}: {v}")
print("    V1 ubezp mc (z marza) = 588")

# ---- 2g. SAMOCHOD ZASTEPCZY ----
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator

rc_calc = ReplacementCarCalculator(rc_rate)
rc_res = rc_calc.calculate_cost(months=MONTHS, enabled=True)
rc_base = float(rc_res["monthly_replacement_car"])
rc_total = float(rc_res.get("total_replacement_car", rc_base * MONTHS))

print("\n  SAMOCHOD ZASTEPCZY:")
for k, v in rc_res.items():
    print(f"    {k}: {v}")
print("    V1 sam.zast mc (z marza) = 70")

# ---- 2h. KOSZTY DODATKOWE ----
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator

class MockInputAdd:
    add_gsm_subscription = True  # CzyGPS=v in V1
    add_hook_installation = True  # CzyHak=v in V1 snapshot = 80
    add_grid_dismantling = False
    add_sales_prep = True  # V1 always includes sales prep
    korekta_kosztu_przygotowania = 0.0

add_res = AdditionalCostsCalculator(settings, MockInputAdd(), MONTHS).calculate_cost()
additional_costs_base = float(add_res["monthly_additional_costs"])
additional_costs_total = additional_costs_base * MONTHS

print("\n  KOSZTY DODATKOWE:")
for k, v in add_res.items():
    print(f"    {k}: {v}")
print("    V1 koszty dod mc (z marza) = 79")

# ---- 2i. SERWIS ----
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput

service_input = ServiceCalculatorInput(
    z_serwisem=True,
    opcja_serwisowa="ASO",
    normatywny_przebieg_mc=1667,
    samar_class_id=int(vehicle.get("samar_class_id", 0)),
    engine_type_id=int(vehicle.get("engine_type_id", 1)),
    power_kw=float(vehicle.get("power_kw", 100)),
    przebieg=TOTAL_KM,
    okres=MONTHS,
    pakiet_serwisowy=0.0,
    inne_koszty_serwisowania_netto=0.0,
)
service_base = ServiceCalculator(service_input).calculate()
service_total = service_base * MONTHS

print("\n  SERWIS:")
print(f"    monthly: {service_base:.2f}")
print(f"    total: {service_total:.2f}")
print("    V1 serwis mc (z marza) = 455")

# ---- 2j. KOSZT DZIENNY ----
from core.LTRSubCalculatorKosztDzienny import KosztDziennyCalculator, KosztDziennyInput

kd_input = KosztDziennyInput(
    utrata_wartosci_z_czynszem=utrata_z_czynszem,
    utrata_wartosci_bez_czynszu=utrata_bez_czynszu,
    koszt_finansowy=finance_res.SumaOdsetekZczynszem,
    samochod_zastepczy_netto=rc_total,
    koszty_dodatkowe_netto=additional_costs_total,
    ubezpieczenie_netto=insurance_total,
    opony_netto=tires_total,
    serwis_netto=service_total,
    suma_odsetek_bez_czynszu=finance_res.SumaOdsetekBEZczynszu,
    okres=MONTHS,
)
kd_result = KosztDziennyCalculator(kd_input).calculate()

print("\n  KOSZT DZIENNY:")
print(f"    koszt_mc: {kd_result.koszt_mc:.2f}")
print(f"    koszt_mc_bez_czynszu: {kd_result.koszt_mc_bez_czynszu:.2f}")
print(f"    koszt_dzienny: {kd_result.koszt_dzienny:.2f}")
print(f"    koszty_ogolem: {kd_result.koszty_ogolem:.2f}")
print("    V1: dzienny=146, ogolem=106280")

# ---- 2k. STAWKA ----
from core.LTRSubCalculatorStawka import StawkaCalculator, StawkaInput

stawka_input = StawkaInput(
    koszt_mc=kd_result.koszt_mc,
    koszt_mc_bez_czynszu=kd_result.koszt_mc_bez_czynszu,
    utrata_wartosci_netto=utrata_z_czynszem,
    koszty_finansowe_netto=finance_res.SumaOdsetekZczynszem,
    ubezpieczenie_netto=insurance_total,
    samochod_zastepczy_netto=rc_total,
    koszty_dodatkowe_netto=additional_costs_total,
    opony_netto=tires_total,
    serwis_netto=service_total,
    okres=MONTHS,
    marza=MARZA_PCT,
    czynsz_inicjalny=float(finance_res.CzynszInicjalnyNetto),
)
stawka_result = StawkaCalculator(stawka_input).calculate()

print("\n  STAWKA:")
print(f"    oferowana_stawka: {stawka_result.oferowana_stawka:.2f}")
print(f"    czynsz_finansowy: {stawka_result.czynsz_finansowy:.2f}")
print(f"    czynsz_techniczny: {stawka_result.czynsz_techniczny:.2f}")
print(f"    marza_mc: {stawka_result.marza_mc:.2f}")
print(f"    marza_na_kontrakcie: {stawka_result.marza_na_kontrakcie:.2f}")

print("\n  ROZKLAD (KosztPlusMarzaKorekta):")
print(f"    Finansowy:     {stawka_result.koszt_finansowy.koszt_plus_marza_korekta:.2f}")
print(f"    Ubezpieczenie: {stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta:.2f}")
print(f"    Serwis:        {stawka_result.koszt_serwis.koszt_plus_marza_korekta:.2f}")
print(f"    Opony:         {stawka_result.koszt_opony.koszt_plus_marza_korekta:.2f}")
print(f"    Sam. zast.:    {stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta:.2f}")
print(f"    Koszty dod.:   {stawka_result.koszt_admin.koszt_plus_marza_korekta:.2f}")

# ---- 3. POROWNANIE ----
print(f"\n{'='*80}")
print("POROWNANIE V1 vs V3 (24mc / 140k / rabat 24% / marza 15%)")
print(f"{'='*80}")

v1 = {
    "Stawka laczna": 5210,
    "Czynsz finansowy": 3798,
    "Czynsz techniczny": 1412,
    "Ubezpieczenie": 588,
    "Serwis": 455,
    "Opony": 220,
    "Sam. zastepczy": 70,
    "Koszty dodatkowe": 79,
    "Koszt dzienny": 146,
    "Koszty ogolem": 106280,
    "Przychod": 125036,
    "Marza kontrakt": 18755,
}

v3 = {
    "Stawka laczna": round(stawka_result.oferowana_stawka, 0),
    "Czynsz finansowy": round(stawka_result.czynsz_finansowy, 0),
    "Czynsz techniczny": round(stawka_result.czynsz_techniczny, 0),
    "Ubezpieczenie": round(stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta, 0),
    "Serwis": round(stawka_result.koszt_serwis.koszt_plus_marza_korekta, 0),
    "Opony": round(stawka_result.koszt_opony.koszt_plus_marza_korekta, 0),
    "Sam. zastepczy": round(stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta, 0),
    "Koszty dodatkowe": round(stawka_result.koszt_admin.koszt_plus_marza_korekta, 0),
    "Koszt dzienny": round(kd_result.koszt_dzienny, 0),
    "Koszty ogolem": round(kd_result.koszty_ogolem, 0),
    "Przychod": round(stawka_result.oferowana_stawka * MONTHS, 0),
    "Marza kontrakt": round(stawka_result.marza_na_kontrakcie, 0),
}

print(f"{'Skladnik':<22} {'V1':>10} {'V3':>10} {'Delta':>10} {'%':>8}")
print("-" * 62)
for key in v1:
    v1v = v1[key]
    v3v = v3.get(key, 0)
    d = v3v - v1v
    p = (d / v1v * 100) if v1v else 0
    f = " !!!" if abs(p) > 5 else " !!" if abs(p) > 2 else " ok"
    print(f"{key:<22} {v1v:>10.0f} {v3v:>10.0f} {d:>+10.0f} {p:>+7.1f}%{f}")

# ---- 4. KOSZTY BAZOWE (bez marzy) ----
print(f"\n{'='*80}")
print("KOSZTY BAZOWE (przed marza)")
print(f"{'='*80}")
print(f"  Ubezpieczenie mc: {insurance_base:.2f}")
print(f"  Serwis mc:        {service_base:.2f}")
print(f"  Opony mc:         {tires_base:.2f}")
print(f"  Sam.zast mc:      {rc_base:.2f}")
print(f"  Koszty dod mc:    {additional_costs_base:.2f}")
print(f"  Finance (odsetki z cz): {finance_res.SumaOdsetekZczynszem:.2f}")
print(f"  Finance (odsetki bez): {finance_res.SumaOdsetekBEZczynszu:.2f}")
print(f"  Utrata z czynszem:     {utrata_z_czynszem:.2f}")
print(f"  Utrata bez czynszu:    {utrata_bez_czynszu:.2f}")
