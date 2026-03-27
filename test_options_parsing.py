
import sys
import os

# Project root is d:\kalk_v3, backend is d:\kalk_v3\backend
project_root = os.path.dirname(os.path.abspath(__file__))
# Add both project root and backend to path should resolve it
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

from core.matrix_cache_job import _parse_price_to_net

def test_option_parsing():
    options = [
        {"name": "Lakier metalizowany", "price": "2 000 PLN brutto", "category": "Karoseria"},
        {"name": "Pakiet Comfort", "price": "4500", "category": "Pakiet"},
        {"name": "Ubezpieczenie", "price": "1500 PLN", "category": "Serwis"},
    ]
    
    print("Testing _parse_price_to_net for options:")
    for opt in options:
        raw_price = opt["price"]
        # In matrix_cache_job.py, is_brutto is often determined by price_domain
        # Let's assume is_brutto=True as it is common for car cards
        parsed = _parse_price_to_net(raw_price, is_brutto=True)
        print(f"Name: {opt['name']} | Raw: {raw_price} | Parsed Net: {parsed}")

if __name__ == "__main__":
    test_option_parsing()
