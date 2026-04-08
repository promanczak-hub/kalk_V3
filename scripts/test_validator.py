import json
from core.pipeline_price_validator import validate_card_summary_prices

with open("test_out.json", "r", encoding="utf-8") as f:
    data = json.load(f)

card_summary = data.get("card_summary", {})
report = validate_card_summary_prices(card_summary)

print("IS VALID:", report.is_valid)
print("WARNINGS:")
for w in report.warnings:
    print(w)
