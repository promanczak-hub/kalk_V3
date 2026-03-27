import asyncio
import json
from core.database import supabase
from core.samar_rv import RVInput, SamarRVCalculator, get_samar_class_id
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
    if not vehicle_dict.get('engine_type_id'):
        vehicle_dict['engine_type_id'] = 1  # 1 is Benzyna usually

    base_gross = 181300.0
    options_gross = 48420.0
    
    calc_input = type('CalcInput', (), {
        'vehicle_vintage': 'current',
        'is_metalic': True,
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
