import os
from dotenv import load_dotenv

# Load env before importing core code so database.py gets correct keys
load_dotenv(r"d:\kalk_v3\backend\.env")

from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony

def main():
    try:
        calc = LTRSubCalculatorOpony(
            z_oponami=True,
            klasa_opony_string="medium",
            srednica_felgi=16,
            sets_needed_override=None,
            odkup_opon_enabled=False
        )
        res = calc.calculate_cost(months=36, total_km=60000, correction_gross=0.0)
        print("Obliczenia zakończone sukcesem:")
        print(f"OponyNetto: {res.get('OponyNetto')}")
        print(res.get('trace')[-1])
    except Exception as e:
        print(f"Błąd podczas inicjalizacji/kalkulacji: {e}")

if __name__ == "__main__":
    main()
