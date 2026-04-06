
import os

def count_lines(path):
    if not os.path.exists(path):
        return "N/A"
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return "ERR"

v1_dir = r"C:\Users\proma\Downloads\kalkulator_V1_extracted\kalkulator_V1"
v3_dir = r"d:\kalk_v3\backend\core"

# Mapping: V1 name -> V3 filename (if different)
components = {
    "LTRKalkulator": "LTRKalkulator.py",
    "LTRSubCalculatorAmortyzacja": "LTRSubCalculatorAmortyzacja.py",
    "LTRSubCalculatorBudzetMarketingowy": "LTRSubCalculatorBudzetMarketingowy.py",
    "LTRSubCalculatorCenaZakupu": "LTRSubCalculatorCenaZakupu.py",
    "LTRSubCalculatorFinanse": "LTRSubCalculatorFinanse.py",
    "LTRSubCalculatorKosztDzienny": "LTRSubCalculatorKosztDzienny.py",
    "LTRSubCalculatorKosztyDodatkowe": "LTRSubCalculatorKosztyDodatkowe.py",
    "LTRSubCalculatorOpony": "LTRSubCalculatorOpony.py",
    "LTRSubCalculatorSamochodZastepczy": "LTRSubCalculatorSamochodZastepczy.py",
    "LTRSubCalculatorSerwis": "LTRSubCalculatorSerwisNew.py",
    "LTRSubCalculatorStawka": "LTRSubCalculatorStawka.py",
    "LTRSubCalculatorUbezpieczenie": "LTRSubCalculatorUbezpieczenie.py",
    "LTRSubCalculatorUtrataWartosci": "LTRSubCalculatorUtrataWartosciNew.py",
}

print(f"{'Component':<40} | {'V1 (C#)':<10} | {'V3 (Python)':<10} | {'Ratio':<10}")
print("-" * 80)

for comp, v3_file in components.items():
    v1_file = comp + ".cs"
    v1_path = os.path.join(v1_dir, v1_file)
    v3_path = os.path.join(v3_dir, v3_file)
    
    v1_l = count_lines(v1_path)
    v3_l = count_lines(v3_path)
    
    ratio = ""
    if isinstance(v1_l, int) and isinstance(v3_l, int) and v3_l > 0:
        ratio = f"{v1_l / v3_l:.2f}x"
        
    print(f"{comp:<40} | {v1_l:<10} | {v3_l:<10} | {ratio:<10}")
