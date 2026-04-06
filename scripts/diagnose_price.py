
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from core.price_parser import parse_price_string

def _parse_price_to_net(price_val, is_brutto):
    try:
        if isinstance(price_val, str):
            parsed = parse_price_string(price_val)
            if parsed is None:
                print(f"DEBUG: parse_price_string returned None for '{price_val}'")
                return 0.0
            val = parsed.value
            print(f"DEBUG: Parsed '{price_val}' -> value={val}, tax_type={parsed.tax_type}")
            if parsed.tax_type == "brutto":
                return round(val / 1.23, 2)
            if parsed.tax_type == "netto":
                return val
        else:
            val = float(price_val)
            print(f"DEBUG: Non-string input {price_val} -> float={val}")

        if is_brutto:
            return round(val / 1.23, 2)
        return val
    except Exception as e:
        print(f"DEBUG: Exception parsing {price_val}: {e}")
        return 0.0

test_cases = [
    ("183 550 PLN brutto", True),
    ("247850 PLN brutto", True),
    ("200450 PLN brutto", True),
    (183550, True),
    ("150000 netto", False),
    ("150000", True),
]

print("--- Testing _parse_price_to_net logic ---")
for val, is_b in test_cases:
    res = _parse_price_to_net(val, is_b)
    print(f"Input: {val!r}, is_brutto={is_b} -> Result: {res}")
