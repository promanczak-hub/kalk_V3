import asyncio
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput

async def main():
    payload = {
        "vehicle_id": "f176456b-af27-4445-92be-cd88246ae83a",
        "base_price_net": 247850.00 - 34500.00 - 200.00,  # Base might be 247850 total before discount? Wait, CenaCennikowa = 247850.
        "discount_pct": 24.0,
        "factory_options": [
            {"name": "Opcje", "price_net": 34500.00, "price_gross": 34500 * 1.23, "is_discountable": True},
            {"name": "Opcje z WR", "price_net": 200.00, "price_gross": 200 * 1.23, "is_discountable": True}
        ],
        "service_options": [],
        "okres_bazowy": 36,
        "przebieg_bazowy": 50000,
        "pricing_margin_pct": 0.0,
        "z_oponami": True,
        "klasa_opony_string": "Premium",
        "srednica_felgi": 19,
        "wibor_pct": 4.82,
        "margin_pct": 2.2,
        "initial_deposit_pct": 0.0,
        "add_gsm_subscription": True,
        "add_sales_prep": True,
        "include_servicing": True,
        "replacement_car_enabled": True,
        "service_cost_type": "ASO",
        "matrix_km_mode": "contract",
        "settings": {
            "settings_version_id": None,
            "overrides": None
        }
    }
    
    calc_input = CalculatorInput(**payload)
    
    from core.database import supabase
    from core.models import ControlCenterSettings
    
    response = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**response.data[0])
    
    kalk = LTRKalkulator(calc_input, settings)
    data = kalk.build_matrix()
    
    import json
    found = False
    for cell in data:
        if cell.get("Okres") == 36 and cell.get("Przebieg") == 50000:
            found = True
            print("\n==== Znaleziono 36 m-cy / 150k km (50k rocznie) ====")
            print(f"Stawka Laczna: {cell['LacznaStawka']}")
            print(f"Czynsz Finansowy: {cell['CzynszFinansowy']}")
            print(f"Czynsz Techniczny: {cell['CzynszTechniczny']}")
            print(f"Ubezpieczenie: {cell['LacznieUbezpieczenie']}")
            print(f"Serwis: {cell['KosztySerwisowe']}")
            print(f"Opony: {cell['LacznyKosztOpon']}")
            print(f"Sam Zastepczy: {cell['LacznieSamochodZastepczy']}")
            print(f"Koszty Dodatkowe: {cell['KosztyDodatkowe']}")
            with open("test.json", "w", encoding="utf-8") as f:
                json.dump(cell, f, indent=2, ensure_ascii=False)
                
    if not found:
        print("Nie znaleziono Przebieg = 50000 dla Okres = 36")

if __name__ == "__main__":
    asyncio.run(main())

