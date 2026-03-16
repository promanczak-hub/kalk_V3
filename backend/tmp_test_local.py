import sys
import os
sys.path.append(os.path.abspath('d:/kalk_v3/backend'))

from core.LTRKalkulator import LTRKalkulator
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
    "przebieg_bazowy": 150000,
    "pricing_margin_pct": 0.0,
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
    "add_sales_prep": False,
    "add_registration": True
}

try:
    response = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**response.data[0])

    inp = CalculatorInput(**data)
    engine = LTRKalkulator(input_data=inp, settings=settings)
    cells = engine.build_matrix()
    print("Cells count:", len(cells))
    if cells:
        print("First cell:")
        print(cells[0])
except Exception:
    import traceback
    traceback.print_exc()
