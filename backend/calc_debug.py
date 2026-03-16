import sys
import os
import json
from dotenv import load_dotenv

# Set working dir to backend for imports
os.chdir(r"d:\kalk_v3\backend")
sys.path.insert(0, r"d:\kalk_v3\backend")
load_dotenv()

from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput
from core.models import ControlCenterSettings
from core.database import supabase

def run():
    print("Fetching settings...")
    response = supabase.table('control_center').select('*').eq('id', 1).execute()
    settings = ControlCenterSettings(**response.data[0])

    data = CalculatorInput(
        calculation_id="debug",
        vehicle_id="test",
        base_price_net=150000.0,
        okres_bazowy=48,
        przebieg_bazowy=160000,
        wibor_pct=4.82,
        margin_pct=2.0,
        pricing_margin_pct=15.0,
        z_oponami=True,
        klasa_opony_string="Premium",
        srednica_felgi=18,
        replacement_car_enabled=True,
        service_cost_type="ASO"
    )

    print("Running calculations...")
    calc = LTRKalkulator(data, settings)
    cells = calc.build_matrix()

    print("Searching for 48m, 160k km (40k/yr) cell...")
    for c in cells:
        if c['Okres'] == 48 and c['Przebieg'] == 160000:
            print("CELL FOUND:")
            important_keys = [
                'LacznaStawka', 'CenaZakupu', 'WartoscPoczatkowa', 'UtrataWartosci',
                'KosztyOgolem', 'LacznyKosztCzesciOdsetkowejRaty',
                'koszty_finansowe_netto', 'koszty_ubezpieczenie_netto', 'koszty_serwis_netto', 'koszty_opony_netto'
            ]
            dump = {k: c.get(k) for k in important_keys}
            dump['CenaZakupu_WartoscPoczatkowa'] = (c.get('CenaZakupu', {}).get('WartoscPoczatkowa'),) 
            print(json.dumps(dump, indent=2, default=str))
            
            # Print breakdown
            breakdown = c.get('breakdown', {})
            print("\nBREAKDOWN:")
            print(json.dumps(breakdown, indent=2))
            break
            
if __name__ == "__main__":
    run()
