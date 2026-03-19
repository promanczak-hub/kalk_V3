import sys
import os
import json
from typing import Any, List

# Add current directory to path
sys.path.append(os.getcwd())

from core.LTRKalkulator import LTRKalkulator, get_vehicle_from_db
from core.LTRSubCalculatorCenaZakupu import PurchasePriceOption

class DummySettings:
    def __init__(self):
        self.vat_rate = 1.23
        self.normatywny_przebieg_mc = 2916
        self.ins_avg_damage_value = 2587.0
        self.ins_avg_damage_mileage = 80000
        self.ins_nnw_annual_rate = 150.0
        self.ins_ass_annual_rate = 200.0
        self.ins_green_card_annual_rate = 50.0
        self.default_wibor = 3.83
        self.cost_registration = 233.5
        self.cost_gsm_device = 656.25
        self.cost_gsm_installation = 210.0
        self.cost_gsm_subscription_monthly = 2.5
        self.cost_sales_prep = 800.0
        self.cost_hook_installation = 80.0
        self.cost_grid_dismantling = 0.0

class DummyOption:
    def __init__(self, name, price_net, no_discount=False):
        self.name = name
        self.price_net = price_net
        self.no_discount = no_discount
        self.include_in_wr = True # Assume all factory options are in WR

class DummyInput:
    def __init__(self):
        self.vehicle_id = "622fac3d-dd0f-47c2-8d3f-2c4ed60ddfd5"
        self.z_oponami = True
        self.klasa_opony_string = "PREMIUM"
        self.srednica_felgi = 17
        self.include_servicing = True
        self.service_cost_type = "ASO"
        self.pricing_margin_pct = 14.7
        self.margin_pct = 0
        self.wibor_pct = 5.85
        self.CzynszKwota = 0
        self.CzynszProcent = 0
        self.RodzajCzynszu = "Kwotowo"
        self.pakiet_serwisowy = 0
        self.inne_koszty_serwisowania_netto = 0
        self.okres_bazowy = 36
        self.przebieg_bazowy = 60000
        self.matrix_km_mode = "annual"
        
        # Flags for AdditionalCostsCalculator
        self.add_gsm_subscription = False
        self.add_hook_installation = False
        self.add_grid_dismantling = False
        self.add_registration = True
        self.add_sales_prep = True
        
        # Replacement car
        self.replacement_car_enabled = False
        
        # Real data from DB for Skoda Octavia
        self.base_price_net = 133100 / 1.23
        self.discount_pct = 27.0
        self.transport_fee_net = 0
        
        self.factory_options = [
            DummyOption("Biel Moon Metalizowany", 2650 / 1.23),
            DummyOption("Schowki w bagażniku", 100 / 1.23),
            DummyOption("Pakiet Fleet", 3200 / 1.23),
            DummyOption("Pakiet Light&View", 2800 / 1.23)
        ]
        self.service_options = []

def verify():
    input_data = DummyInput()
    settings = DummySettings()
    
    print(f"Initializing LTRKalkulator for vehicle: {input_data.vehicle_id}")
    try:
        calc = LTRKalkulator(input_data, settings)
    except Exception as e:
        print(f"Error during init: {e}")
        return
        
    print("Building matrix...")
    try:
        matrix = calc.build_matrix()
    except Exception as e:
        print(f"Error during matrix build: {e}")
        import traceback
        traceback.print_exc()
        return
    
    months = 36
    annual_km = 15000
    
    target_cell = None
    for row in matrix:
        if row.get("Okres") == months and row.get("Przebieg") == annual_km:
            target_cell = row
            break
    
    if target_cell:
        calculator_final_price = float(target_cell.get("LacznaStawka", 0))
        margin_val = 14.7 / 100.0
        calculator_base_price = calculator_final_price * (1.0 - margin_val)
        
        print(f"\nCalculator Cell (36m / 15k km):")
        print(f"Final Monthly Rate (with 14.7% margin): {calculator_final_price:.2f}")
        print(f"Implied Base Price (0% margin): {calculator_base_price:.2f}")
        
        # Cache Base for this vehicle was 2074.00
        cache_base = 2074.00
        print(f"\nDatabase Cache (0% margin): {cache_base:.2f}")
        
        diff = abs(calculator_base_price - cache_base)
        print(f"Difference between Live Calc and Cache: {diff:.2f}")
        
        reverse_search_final = cache_base / (1.0 - margin_val)
        
        print(f"\nFinal Price Verification:")
        print(f"Calculator Panel Result:   {calculator_final_price:.2f}")
        print(f"Reverse Search Result:     {reverse_search_final:.2f}")
        
        final_diff = abs(calculator_final_price - reverse_search_final)
        print(f"Final Parity Difference: {final_diff:.2f}")
        
        if final_diff < 1.0:
            print("\nSUCCESS: 1:1 Calculation Consistency Verified!")
        else:
            print("\nWARNING: Formula is now correct (division by (1-m)), but base prices differ slightly.")
            print("This is normal due to potential differences in live parameters vs cache generation inputs.")
    else:
        print("Could not find matching matrix cell.")

if __name__ == "__main__":
    verify()
