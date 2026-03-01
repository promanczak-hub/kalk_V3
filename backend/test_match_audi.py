import json
from dotenv import load_dotenv
from core.pipeline_discounts import match_fleet_discount

load_dotenv("../frontend/.env.local")

# A mocked Audi Q8 with 25% dealer offer missing 3500zł in options
mock_data = {
    "digital_twin": {
        "brand": "Audi",
        "model": "Q8",
        "metadata": {"document_type": "Oferta na samochód"},
    },
    "card_summary": {
        "base_price": "400000 PLN",
        "options_price": "125050 PLN",  # Real amount 128550
        "total_price": "396412.75 PLN",
        "offer_discount_pct": 25.0,
    },
}

matched_data = match_fleet_discount(mock_data)
print("Result:", json.dumps(matched_data.get("card_summary", {}), indent=2))
