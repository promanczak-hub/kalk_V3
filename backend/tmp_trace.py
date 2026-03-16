import sys
import os
sys.path.append(os.path.abspath('d:/kalk_v3/backend'))

from core.PipelineDebugger import PipelineDebugger
from api.schemas.calculator import CalculatorInput
from core.database import supabase
from core.models import ControlCenterSettings

data = {
    "vehicle_id": "bd5e546f-9d90-428e-b144-dd9588fd02f1",
    "base_price_net": 135406.50,
    "discount_pct": 27.0,
    "factory_options": [
        {"name": "Szary Steel", "price_net": 2154.47, "price_gross": 2650.0, "no_discount": False, "include_in_wr": True},
        {"name": "Design", "price_net": 1544.72, "price_gross": 1900.0, "no_discount": False, "include_in_wr": True},
        {"name": "Pakiet Winter", "price_net": 975.61, "price_gross": 1200.0, "no_discount": False, "include_in_wr": True},
        {"name": "Pakiet Info", "price_net": 4146.34, "price_gross": 5100.0, "no_discount": False, "include_in_wr": True},
        {"name": "Kierownica", "price_net": 487.80, "price_gross": 600.0, "no_discount": False, "include_in_wr": True},
        {"name": "Pakiet Assist", "price_net": 569.11, "price_gross": 700.0, "no_discount": False, "include_in_wr": True},
        {"name": "Zapasowe", "price_net": 569.11, "price_gross": 700.0, "no_discount": False, "include_in_wr": True}
    ],
    "service_options": [
        {"name": "Opcje serwisowe", "price_gross": 1065.4875, "price_net": 866.25, "no_discount": True, "include_in_wr": False}
    ],
    "okres_bazowy": 36,
    "przebieg_bazowy": 50000,
    "pricing_margin_pct": 15.0,
    "wibor_pct": 3.83,
    "margin_pct": 2.2,
    "z_oponami": True,
    "srednica_felgi": 17,
    "klasa_opony_string": "Medium",
    "replacement_car_enabled": True,
    "samar_category": "SAMAR: Podstawowa - C NIŻSZA ŚREDNIA",
    "engine_name": "SILNIK: Diesel (ON)",
    "body_type_name": "Kombi",
    "add_gsm_subscription": True,
    "add_sales_prep": True,
    "add_registration": True
}

with open("trace_out.txt", "w", encoding="utf-8") as f:
    try:
        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        settings = ControlCenterSettings(**response.data[0])

        inp = CalculatorInput(**data)
        debugger = PipelineDebugger(input_data=inp, settings=settings)
        # Przebieg_bazowy is yearly, so we want 50000? No, wait!
        # PRZEBIEG 50000 z tabeli = 50 000 km rocznie? LTR matrix has 50000 km/year or total?
        # In calculator_core_routes and tests, it's 50000 per year. Let's just generate steps for months=36.
        # Wait, the UI passes km_per_year? PipelineDebugger doesn't take km_per_year directly, it uses przebieg_bazowy from `CalculatorInput` which is total.
        # If I want to trace 50000 km/year for 36 months, total_km = 150000.
        inp.przebieg_bazowy = 150000
        inp.okres_bazowy = 36
        
        steps = debugger.calculate_steps(months=36, overrides={})
        
        for step in steps:
            f.write("\n========================================\n")
            f.write(f"KROK {step['step']}: {step['name']}\n")
            f.write("========================================\n")
            
            f.write("\n-- WYNIKI (OUTPUTS) --\n")
            for k, v in step.get("outputs", {}).items():
                f.write(f"  {k} = {v}\n")
                
            f.write("\n-- ŚLAD (TRACE) --\n")
            for tr in step.get("trace", []):
                if isinstance(tr, dict):
                    f.write(f"  [{tr.get('krok', 'Krok')}]: {tr.get('wynik', '')}\n")
                    if tr.get('rownanie'):
                        f.write(f"      ( {tr.get('rownanie')} )\n")
                else:
                    f.write(f"  {tr}\n")
                    
    except Exception:
        import traceback
        f.write(traceback.format_exc())
