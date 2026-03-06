import os
from dotenv import load_dotenv

# Wczytujemy z .env.local
load_dotenv(".env.local")

from core.database import supabase
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
from core.LTRSubCalculatorAmortyzacja import AmortyzacjaCalculator, AmortyzacjaInput
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew
from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput


def get_rates(klasa_id):
    res = (
        supabase.table("ltr_admin_ubezpieczenia")
        .select("*")
        .eq("KlasaId", klasa_id)
        .execute()
    )
    return res.data if res.data else []


def get_damage(klasa_id):
    res = (
        supabase.table("ltr_admin_wspolczynniki_szkodowe")
        .select("*")
        .eq("klasa_wr_id", klasa_id)
        .execute()
    )
    return res.data[0] if res.data else {}


# Znajdźmy auto, które ma przypisaną klasę ubezpieczeniową i szkodową
print("Użyto zmockowanego pojazdu z przypisaną Klasą 9 do testów matematycznych.")
klasa_wr_id = 9
r = get_rates(klasa_wr_id)
d = get_damage(klasa_wr_id)
if r and d:
    selected_bez_fallbacku = {
        "id": "mock-123",
        "marka": "TestBrand",
        "model": "TestModel",
        "klasa_wr_id": klasa_wr_id,
        "cena": 100000.0,
        "engine_type_id": 1,
        "power_kw": 110.0,
    }
    rates = r
    damage = d

if not selected_bez_fallbacku:
    print("Nie znaleziono stawek dla mockowanej klasy 9.")
    exit(1)

print(
    f"Wybrane auto: {selected_bez_fallbacku['marka']} {selected_bez_fallbacku['model']} (ID: {selected_bez_fallbacku['id']} Klasa_WR_ID: {selected_bez_fallbacku['klasa_wr_id']})"
)
print(f"Liczba stawek AC: {len(rates)}")
print(f"Dane szkodowe: {damage}")

# Założenia kalkulacji:
MONTHS = 48
TOTAL_KM = 140000
MARGIN = 12.0  # 12%
BASE_PRICE = float(selected_bez_fallbacku.get("cena", 100000.0) or 100000.0)

print(f"Kwota zakupu brutto do symulacji RV: {BASE_PRICE * 1.23}")
base_price_net = BASE_PRICE


# Ustawienia dodatkowe:
class MockSettings:
    def __init__(self):
        self.wymagane_doubezpieczenie_kradziezy = False
        self.wymagane_od_ryzyk_nauka_jazdy = False
        self.marza_ubezpieczenie_procent = MARGIN  # Ubezpieczenie stosuje marze?
        self.sredni_przebieg_dla_szkody = 30000.0
        self.srednia_wartosc_szkody = 1500.0
        self.ins_avg_damage_value = 1500.0
        self.ins_avg_damage_mileage = 30000.0
        self.ins_theft_doub_pct = 0.0
        self.ins_driving_school_doub_pct = 0.0
        self.samar_rv_apply_options_depreciation = False
        self.samar_rv_base_mileage = 15000
        self.samar_rv_mileage_unit_km = 1000


mock_settings = MockSettings()


# 1. Obliczamy RV żeby mieć amortyzację.
class MockInputData:
    def __init__(self):
        self.pricing_margin_pct = MARGIN
        self.factory_options = []
        self.service_options = []
        self.settings = mock_settings


mock_input = MockInputData()

rv_calc = LTRSubCalculatorUtrataWartosciNew(selected_bez_fallbacku, mock_input)  # type: ignore
rv_res = rv_calc.calculate_values(
    months=MONTHS,
    total_km=TOTAL_KM,
    base_vehicle_capex_gross=base_price_net * 1.23,
    options_capex_gross=0,
)
vr_samar = rv_res["WR"]

print(f"Wartość rezydualna z SAMAR (netto): {vr_samar}")

# Obliczamy miesięczną wartość amortyzacyjną (jak V1)
from core.LTRSubCalculatorAmortyzacja import AmortyzacjaCalculator, AmortyzacjaInput

amort_input = AmortyzacjaInput(wp=base_price_net, wr=vr_samar, okres=MONTHS)
amort_result = AmortyzacjaCalculator(amort_input).calculate()
procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

print(f"Amortyzacja miesięcznie: {procent_amortyzacji_miesiecznie}")

# Wywołujemy nowy kalkulator
ins_calc = InsuranceCalculator(
    insurance_rates=rates,
    damage_coefficients=damage,
    settings=mock_settings,  # type: ignore
    amortization_pct=procent_amortyzacji_miesiecznie,
    total_km=TOTAL_KM,
)

ins_res = ins_calc.calculate_cost(MONTHS, base_price_net)
ins_month = float(ins_res["monthly_insurance"])
ins_total = float(ins_res.get("total_insurance", ins_month * MONTHS))

print("\n--- WYNIKI KALKULACJI UBEZPIECZENIA ---")
print(f"Ubezpieczenie MC: {ins_month:.2f} PLN")
print(f"Ubezpieczenie Razem ({MONTHS} m-cy): {ins_total:.2f} PLN")
print("\nSzczegóły wewnętrzne (netto bez marży/leasing):")
print(ins_res)
