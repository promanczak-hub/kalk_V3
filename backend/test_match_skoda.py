import json
from core.pipeline_discounts import match_fleet_discount
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")

pro_data = {
    "digital_twin": {
        "metadata": {"document_type": "Oferta na samochód"},
        "brand": "SKODA",
        "model": "Kamiq",
    },
    "card_summary": {
        "base_price": 91951.22,
        "options_price": 2357.72,
        "total_price": 94308.94,
    },
    "offer_details": {
        "vehicle": {"make": "SKODA", "model": "Kamiq", "version": "Selection"}
    },
}

print("Running match_fleet_discount...")
result = match_fleet_discount(pro_data)
print("Result card_summary:")
print(json.dumps(result.get("card_summary"), indent=2))
