from api.schemas.calculator import CalculatorInput
from core.LTRKalkulator import LTRKalkulator
from core.models import ControlCenterSettings
from core.database import supabase

payload = {
  "vehicle_id": "bd5e546f-9d90-428e-b144-dd9588fd02f1",
  "base_price_net": 100000.0,
  "samar_category": "Podstawowa - B MAŁE",
  "samar_class_id": 101,
  "engine_type_id": 1,
  "power_kw": 100,
  "matrix_km_mode": "contract",
  "okres_bazowy": 48,
  "matrix_contract_km_min": 40000,
  "matrix_contract_km_max": 240000,
  "matrix_contract_km_step": 10000,
  "include_servicing": False,
  "z_oponami": True,
  "srednica_felgi": 17,
  "body_type_name": "Sedan"
}

try:
    data = CalculatorInput(**payload)
    response = supabase.table("control_center").select("*").eq("id", 1).execute()
    settings = ControlCenterSettings(**response.data[0])
    engine = LTRKalkulator(input_data=data, settings=settings)
    cells = engine.build_matrix()
    print('Number of cells:', len(cells))
    for c in cells:
        print(f"Okres: {c.get('Okres'):2}, Prz_Kont: {c.get('PrzebiegKontrakt'):6}, Prz_Rocz: {c.get('Przebieg'):6}")
except Exception:
    import traceback
    traceback.print_exc()
