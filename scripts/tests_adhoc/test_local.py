import sys

sys.path.insert(0, r"d:\kalk_v3\backend")
import json
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput
from core.models import ControlCenterSettings


def main():
    payload = {
        "okres_miesiecy": [36],
        "przebieg_roczny": [60000],
        "base_price_net": 161765.03,
        "discount_pct": 0.0,
        "factory_options": [],
        "service_options": [],
        "wibor_pct": 4.82,
        "margin_pct": 2.0,
        "pricing_margin_pct": 13.0,
        "srednica_felgi": 19,
        "profil_opony": 40,
        "klasa_opony_string": "Premium",
        "vehicle_id": "c81aac34-abeb-4dc7-884a-6c26488c099b",
    }

    input_data = CalculatorInput(**payload)
    settings = ControlCenterSettings()
    calc = LTRKalkulator(input_data, settings)
    cells = calc.calculate()
    target = [x for x in cells if x["months"] == 36 and x["km_per_year"] == 60000]
    if target:
        c = target[0]
        print("RATE:", c["price_net"])
        print("BASE:", c["base_cost_net"])
        # Also print some debug if we want
        print(json.dumps(c["breakdown"], indent=2))


if __name__ == "__main__":
    main()
