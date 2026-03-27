import os
import json
from dotenv import load_dotenv
from google.genai import types, Client

load_dotenv("../frontend/.env.local")
load_dotenv()

key = os.environ.get("GEMINI_API_KEY")
gemini_client = Client(api_key=key)

with open("extracted_samar.md", "r", encoding="utf-8") as f:
    text = f.read()

prompt = f"""
Przeanalizuj poniższy tekst z PDF "Segmentacja rynku SAMAR 2025".
Twoim zadaniem jest wyciągnięcie listy przykładowych modeli samochodów przypisanych do poszczególnych GRUP i KLAS, i zmapowanie ich na naszą oficjalną nomenklaturę 33 klas SAMAR.

Oto docelowa lista naszych 33 klas (format "Grupa - Klasa Wielkości"):
Autobusy - AUTOBUSY
Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE
Kombivany - H KOMBI-VANY
Lekkie dostawcze - KOMBI VAN
Lekkie dostawcze - VAN
Minibusy - I MINIBUSY
Pick-up - PICK-UP
Podstawowa - A MINI
Podstawowa - B MAŁE
Podstawowa - C NIŻSZA ŚREDNIA
Podstawowa - D ŚREDNIA
Podstawowa - E WYŻSZA
Podstawowa - F LUKSUSOWE
Podstawowa - G SUPER LUKSUSOWE
Sportowo-rekreacyjne - A MINI
Sportowo-rekreacyjne - B MAŁE
Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA
Sportowo-rekreacyjne - D ŚREDNIA
Sportowo-rekreacyjne - E WYŻSZA
Sportowo-rekreacyjne - F LUKSUSOWE
Sportowo-rekreacyjne - G SUPER LUKSUSOWE
Średnie dostawcze - ŚREDNIE DOSTAWCZE
Terenowo-rekreacyjne (SUV) - B MAŁE
Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA
Terenowo-rekreacyjne (SUV) - D ŚREDNIA
Terenowo-rekreacyjne (SUV) - E WYŻSZA
Terenowo-rekreacyjne (SUV) - F LUKSUSOWE
Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE
Vany - B MICROVANY
Vany - C MINIVANY
Vany - D VANY
Vany - E WYŻSZA
Vany - F LUKSUSOWE

Tekst z PDF do analizy:
{text}

Odfiltruj puste miejsca. Dla każdej klasy z wymienionych 33 klas złącz wyciągnięte modele w jeden ciąg tekstowy oddzielony przecinkami (np. "Audi A3/S3/RS3, BMW Serii 1, BYD Dolphin..."). Pomijaj numerację "1.", "2." itp.
Dla klas których w pdf nie znajdziesz rzuć puste ciągi.
"""

response = gemini_client.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.0,
        response_schema={
            "type": "object",
            "properties": {
                "mappings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "class_name": {"type": "string"},
                            "models_str": {"type": "string"},
                        },
                        "required": ["class_name", "models_str"],
                    },
                }
            },
            "required": ["mappings"],
        },
    ),
)

results = json.loads(response.text)

sql_updates = "BEGIN;\n"
for mapping in results.get("mappings", []):
    cls_name = mapping["class_name"].replace("'", "''")
    mods = mapping["models_str"].replace("'", "''")
    if mods.strip():
        sql_updates += f"UPDATE samar_classes SET example_models = '{mods}' WHERE name = '{cls_name}';\n"
sql_updates += "COMMIT;\n"

with open("seed_example_models.sql", "w", encoding="utf-8") as f:
    f.write(sql_updates)

from core.database import supabase

print("Wykonuję update na bazie bezpośrednio...")
for mapping in results.get("mappings", []):
    cname = mapping["class_name"]
    mods = mapping["models_str"]
    if mods.strip():
        res = (
            supabase.table("samar_classes")
            .update({"example_models": mods})
            .eq("name", cname)
            .execute()
        )
        print(f"Zaktualizowano klasę: {cname} (Modele: {len(mods.split(','))})")

print("Zakończono aktualizację bazy online we wskazanym celu.")
