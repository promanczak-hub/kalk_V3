import asyncio
import json
from core.database import supabase
from core.samar_rv import get_samar_class_id
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew

async def main():
    vehicle_id = "5702edb9-14c9-4aa3-85a8-f67692799986"
    synth_res = supabase.table('vehicle_synthesis').select('*').eq('id', vehicle_id).execute()
    vehicle_dict = synth_res.data[0]
    
    # We need to simulate the exact input LTRKalkulator passes
    months = 48
    total_km = 140000
    
    # Let's fix missing samar class ID.
    category = "D ŚREDNIA"
    class_id = get_samar_class_id(category)
    if not class_id:
        class_id = get_samar_class_id("Podstawowa - D ŚREDNIA")
    vehicle_dict["samar_class_id"] = class_id or 10  # fallback
    
    # Fix engine id if missing
    # Exact inputs matching Excel row 1680:
    samar_class_id = 10
    engine_id = 1
    total_km = 120000
    months = 48
    
    # Netto based on Brutto from Excel (181300 / 1.23) and (41600 / 1.23)
    base_gross = 181300.0
    options_gross = 41600.0
    catalog_base_net = base_gross / 1.23
    catalog_options_net = options_gross / 1.23
    rocznik = "current"
    # Inject missing fields into vehicle_dict to avoid errors in SubCalc fallback
    vehicle_dict["engine_type_id"] = engine_id
    vehicle_dict["samar_class_id"] = samar_class_id
    
    calc_input = type('CalcInput', (), {
        'vehicle_vintage': rocznik,
        'months': months,
        'total_km': total_km,
        'engine_id': engine_id,
        'brand_name': 'Skoda',
        'model_name': 'Octavia',
        'paint_type_id': 1,
        'is_metalic': False,
        'body_type_id': 3,
        'samar_class_id': samar_class_id,
        'capex_base_gross': base_gross,
        'capex_options_gross': options_gross,
        'catalog_base_gross': base_gross,
        'catalog_options_gross': options_gross,
        'settings': type('Settings', (), {'vat_rate': 1.23})()
    })()

    try:
        wrapper = LTRSubCalculatorUtrataWartosciNew(vehicle_dict, calc_input)
        print("Samar class ID:", wrapper.samar_class_id)
        print("Engine ID:", wrapper.engine_id)
        
        result = wrapper.calculate_values(
            months=months,
            total_km=total_km,
            base_vehicle_catalog_gross=base_gross,
            options_catalog_gross=options_gross
        )
        print("\n--- RESULTS ---")
        print("WR:", result['WR'])
        print("WR_Gross:", result['WR_Gross'])
        print("WR_percent:", result['WR_percent'])
        print("UtrataWartosciBEZczynszu:", result["UtrataWartosciBEZczynszu"])
        print("\n--- TRACE ---")
        print(json.dumps(result['trace'], indent=2, ensure_ascii=False))
        
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == '__main__':
    asyncio.run(main())
