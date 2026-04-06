import asyncio
import os
import sys
import json

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.core.LTRKalkulator import LTRKalkulator
from backend.api.schemas.calculator import CalculatorInput, VehicleOptions

async def diagnose():
    input_data = CalculatorInput(
        vehicle_id="117a61bf-9488-4b61-a1c3-1461f25fdea5",
        brand="SKODA",
        model="Superb Combi L&K",
        base_price_net=201504.07,
        discount_pct=24.0,
        okres_bazowy=36,
        przebieg_bazowy=20000,
        wibor_pct=3.83,
        margin_pct=2.2,
        initial_deposit_pct=0,
        is_metalic=True,
        add_gsm_subscription=True,
        add_hook_installation=True,
        add_registration=True,
        add_sales_prep=True,
        include_servicing=True,
        replacement_car_enabled=True,
        samar_category="Podstawowa - D ŚREDNIA",
        engine_name="Diesel",
        power_kw=142.0,
        z_oponami=True,
        srednica_felgi=19,
        klasa_opony_string="Medium",
        factory_options=[
            VehicleOptions(name="Options total", price_net=28211.38, price_gross=34700.0)
        ]
    )
    
    class MockSettings:
        def __init__(self):
            self.vat_rate = 1.23
            self.cost_gsm_device = 469.0
            self.cost_gsm_installation = 150.0
            self.normatywny_przebieg_mc = 1667
            self.budzet_marketingowy_ltr = 0.015
            self.cost_gsm_subscription_monthly = 0.0
            self.cost_hook_installation = 1200.0
            self.cost_grid_dismantling = 300.0
            self.cost_registration = 150.0
            self.cost_sales_prep = 1040.0
            self.ins_avg_damage_value = 1200.0
            self.ins_avg_damage_mileage = 150000
            self.ins_nnw_annual_rate = 150.0
            self.ins_ass_annual_rate = 200.0
            self.ins_green_card_annual_rate = 50.0
            
    settings = MockSettings()
    
    print("--- ROZPOCZECIE DIAGNOSTYKI (V4 FIXED) ---")
    calc = LTRKalkulator(input_data=input_data, settings=settings)
    
    matrix = calc.build_matrix(only_exact=False)
    
    for cell in matrix:
        if cell["Okres"] == 36 and cell["Przebieg"] == 20000:
            print("\n--- ZNALEZIONO KOMÓRKĘ 36/20000 ---")
            print(f"STAWKA LACZNA (Netto): {cell['LacznaStawka']} PLN")
            print(f"  - Czynsz Finansowy: {cell['CzynszFinansowy']} PLN")
            print(f"  - Czynsz Techniczny: {cell['CzynszTechniczny']} PLN")
            print(f"    - Ubezpieczenie: {cell['Ubezpieczenie']} PLN")
            print(f"    - Serwis: {cell['Serwis']} PLN")
            print(f"    - Opony: {cell['Opony']} PLN")
            print(f"    - Samochod Zastepczy: {cell['SamochodZastepczy']} PLN")
            print(f"    - Admin: {cell['Admin']} PLN")
            
            for t in cell.get("calculation_trace", []):
                if isinstance(t, dict):
                    krok = str(t.get("krok", ""))
                    if "Finanse (PMT)" in krok:
                        print(f"\nTRACE FINANSE: {json.dumps(t, indent=2, ensure_ascii=False)}")
                    if "Ubezpieczenie" in krok:
                        print(f"\nTRACE UBEZPIECZENIE: {json.dumps(t, indent=2, ensure_ascii=False)}")
            return

    print("\nNie znaleziono 36/20000.")

if __name__ == "__main__":
    asyncio.run(diagnose())
