import sys
import json
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import supabase

# Pobieramy najnowszy Kodiaq by model
response = (
    supabase.table("vehicle_synthesis")
    .select("id, offer_number, synthesis_data")
    .ilike("model", "%Kodiaq%")
    .order("created_at", desc=True)
    .limit(1)
    .execute()
)

if not response.data:
    print("No data found for Kodiaq")
    sys.exit(1)

data = response.data[0]
synthesis_data = data.get("synthesis_data", {})
digital_twin = synthesis_data.get("digital_twin", {})
card_summary = synthesis_data.get("card_summary", {})

print("ID:", data["id"])
print("Offer Number:", data["offer_number"])

# Piszemy do plików aby łatwo przejrzeć
with open("scripts/kodiaq_digital_twin.json", "w", encoding="utf-8") as f:
    json.dump(digital_twin, f, indent=2, ensure_ascii=False)

with open("scripts/kodiaq_card_summary.json", "w", encoding="utf-8") as f:
    json.dump(card_summary, f, indent=2, ensure_ascii=False)

print("Saved scripts/kodiaq_digital_twin.json and scripts/kodiaq_card_summary.json")

# Szukamy kluczowych informacji w digital_twin
print("\n--- Szukanie base_price w digital_twin ---")
pricing = digital_twin.get("pricing", {})
fin_summary = digital_twin.get("financial_summary", {})
print("pricing:", json.dumps(pricing, indent=2, ensure_ascii=False))
print("financial_summary:", json.dumps(fin_summary, indent=2, ensure_ascii=False))

print("\n--- Szukanie power_hp w digital_twin ---")
tech_data = digital_twin.get("technical_data", {})
technical = digital_twin.get("technical", {})
print("technical_data:", json.dumps(tech_data, indent=2, ensure_ascii=False))
print("technical:", json.dumps(technical, indent=2, ensure_ascii=False))
