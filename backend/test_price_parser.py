import json

def _parse_price_to_net(price_val, is_brutto):
    try:
        if isinstance(price_val, str):
            clean = "".join(c for c in price_val if c.isdigit() or c in ".,")
            clean = clean.replace(",", ".")
            if not clean:
                return 0.0
            val = float(clean)
        else:
            val = float(price_val)
            
        if is_brutto:
            return val / 1.23
        return val
    except Exception as e:
        print(f"Error parsing {price_val}: {e}")
        return 0.0

print(_parse_price_to_net("166 760 PLN netto", False))
print(_parse_price_to_net("206600 PLN brutto", True))
print(_parse_price_to_net("207640 PLN netto", False))
