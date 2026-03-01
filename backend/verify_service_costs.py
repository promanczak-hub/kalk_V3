import asyncio
import json
import os
from typing import Any, cast

from google import genai
from google.genai import types

from core.database import supabase
from core.json_utils import clean_json_response


async def run_verification():
    print("Fetching dependencies from Supabase...")

    # Przeniesienie mapowania przykladowych modeli tak jak w glownym backendzie
    samar_czak = supabase.table("KlasaSAMAR_czak").select("col_1", "col_8").execute()
    czak_data = cast(Any, samar_czak.data)
    czak_mapping = {
        row.get("col_1"): row.get("col_8") for row in czak_data if row.get("col_1")
    }

    # Klasy SAMAR
    classes_res = supabase.table("samar_classes").select("*").execute()
    classes = {c["id"]: c for c in classes_res.data}

    for c_id, c_data in classes.items():
        if c_data["name"] in czak_mapping:
            c_data["example_models"] = czak_mapping[c_data["name"]]

    # Silniki
    engines_res = supabase.table("engines").select("*").execute()
    engines = {e["id"]: e for e in engines_res.data}

    # Koszty do weryfikacji
    costs_res = supabase.table("samar_service_costs").select("*").execute()
    costs = costs_res.data

    if not costs:
        print("Brak wpisów w tabeli samar_service_costs.")
        return

    print(f"Found {len(costs)} combinations to verify.")

    # Inicjalizacja Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)

    flash_model_id = "gemini-2.5-flash"

    system_instruction = """
    Jesteś analitykiem kosztów w polskiej firmie flotowej (wynajem, leasing). 
    Twoim zadaniem jest oszacowanie uśrednionego jednostkowego kosztu serwisowego wymaganego do przejechania 1 kilometra w PLN netto.
    
    Koszt ten obejmuje: przeglądy wymagane przez producenta, wymiany części eksploatacyjnych (klocki, tarcze, filtry, wycieraczki, zawieszenie). Nie obejmuje opon, ubezpieczenia, ani paliwa.
    Zazwyczaj dla małych aut miejskich na benzynie to kwoty ok. 0.05 - 0.07 PLN / km.
    Dla dużych SUVów premium, sportowych czy luksusowych to kwoty od 0.15 PLN wzwyż w ASO.
    Koszty w serwisach niezależnych (Non-ASO) są zazwyczaj o 20-35% niższe niż w ASO, rzadziej o połowę dla bardzo drogich aut.
    Zależności:
    - Auta o wyższej klasie -> droższe części i robocizna
    - Auta z większą mocą (HIGH) -> szybsze zużycie hamulców, czasem większe litraże oleju
    - Hybrydy -> wolniej zużywają hamulce (rekuperacja)
    - Auta elektryczne -> brak wymiany oleju, bardzo tanie serwisy napędowe, ale mogą mieć drogie elementy zawieszenia / dedykowane filtry
    
    Zwracaj racjonalnie i profesjonalnie dobrane parametry bazując na obecnych cenach rynkowych.
    """

    for i, cost in enumerate(costs):
        c_class = classes.get(cost["samar_class_id"], {})
        c_engine = engines.get(cost["engine_type_id"], {})

        class_name = c_class.get("name", "Nieznana")
        example_models = c_class.get("example_models", "Brak podpowiedzi")
        engine_name = c_engine.get("name", "Nieznany")
        engine_cat = c_engine.get("category", "Brak")
        power_band = cost.get("power_band", "Brak")

        prompt = f"""
        Oszacuj koszt dla następującego profilu pojazdu we flocie:
        
        Segment/Klasa SAMAR: {class_name}
        Przykładowe modele z tego segmentu: {example_models}
        
        Napęd / Silnik: {engine_name} ({engine_cat})
        Przedział mocy: {power_band} (LOW: do 130KM, MID: 131-200KM, HIGH: >200KM)
        
        Wycena ma być wyrażona w formacie FLOAT (części dziesiętne groszy jako ułamek po kropce np. 0.084) za 1 przejechany kilometr.
        """

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,  # Low temperature for consistent business logic
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "cost_aso_per_km": {
                        "type": "number",
                        "description": "Szacowany jednostkowy koszt napraw i przeglądów dla Autoryzowanych Stacji Obsługi (w PLN Netto na 1 km).",
                    },
                    "cost_non_aso_per_km": {
                        "type": "number",
                        "description": "Szacowany jednostkowy koszt napraw i przeglądów dla Serwisów Niezależnych (w PLN Netto na 1 km).",
                    },
                },
                "required": ["cost_aso_per_km", "cost_non_aso_per_km"],
            },
        )

        try:
            old_aso = cost["cost_aso_per_km"]
            old_non_aso = cost["cost_non_aso_per_km"]

            # Only verify if logic determines we should (for testing let's do all)
            response = client.models.generate_content(
                model=flash_model_id,
                contents=[types.Part.from_text(text=prompt)],
                config=config,
            )

            resp_text = getattr(response, "text", "{}") or "{}"
            result = json.loads(clean_json_response(str(resp_text)))

            new_aso = result.get("cost_aso_per_km", old_aso)
            new_non_aso = result.get("cost_non_aso_per_km", old_non_aso)

            print(f"[{i + 1}/{len(costs)}] {class_name} | {engine_name} | {power_band}")
            print(f"   -> Old: ASO={old_aso}, Non-ASO={old_non_aso}")
            print(f"   -> New: ASO={new_aso}, Non-ASO={new_non_aso}")

            # Zakończ update na bazie danych
            supabase.table("samar_service_costs").update(
                {"cost_aso_per_km": new_aso, "cost_non_aso_per_km": new_non_aso}
            ).eq("id", cost["id"]).execute()

            print("   -> (Zaktualizowano w bazie)\n")

            # Small delay to avoid API rate limiting in loop if there are many combination
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Rozpoznany wyjątek w kroku {i + 1}: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_verification())
