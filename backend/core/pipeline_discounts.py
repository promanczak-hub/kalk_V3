import json
import os
from supabase import create_client, Client
from google import genai
from google.genai import types

from core.json_utils import clean_json_response
from core.prompts import MATCH_FLEET_DISCOUNT_SYSTEM_PROMPT


def match_fleet_discount(pro_data: dict) -> dict:
    """
    Given the extracted digital twin JSON, queries Supabase for matching fleet discounts,
    uses Gemini to determine the best match, and appends the result to `pro_data` via `card_summary`.
    """
    # 1. Sprawdź czy mamy w ogóle wyciągnięty obiekt i brand
    flash_data = pro_data.get("card_summary", {})
    metadata = pro_data.get("digital_twin", {}).get("metadata", {})
    extracted_brand = pro_data.get("brand") or pro_data.get("digital_twin", {}).get(
        "brand", ""
    )

    doc_type_str = metadata.get("document_type", "Oferta na samochód")

    if not extracted_brand or doc_type_str != "Oferta na samochód":
        return pro_data

    # 2. Skonfiguruj API
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)

    flash_model_id = "gemini-2.5-flash"

    try:
        # Setup Supabase client safely
        supabase_url = os.environ.get("VITE_SUPABASE_URL")
        supabase_key = os.environ.get("VITE_SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            return pro_data

        supabase: Client = create_client(supabase_url, supabase_key)

        # 3. Pobierz wszystkie potencjalne wiersze z bazy danych
        # Zrezygnowano ze sztywnego filtra ILIKE marka, aby LLM sam łaczył VW z Volkswagen itp.
        supabase_response = supabase.table("tabela_rabaty").select("*").execute()

        discount_rows = supabase_response.data

        if not discount_rows:
            return pro_data

        # ── Brand pre-check: skip LLM if brand doesn't exist in DB ──
        brand_aliases: dict[str, set[str]] = {
            "volkswagen": {"vw", "volkswagen", "vw osobowe", "vw dostawcze"},
            "vw": {"vw", "volkswagen", "vw osobowe", "vw dostawcze"},
            "vw osobowe": {"vw", "volkswagen", "vw osobowe"},
            "vw dostawcze": {"vw", "volkswagen", "vw dostawcze"},
            "seat": {"seat", "seat/cupra", "cupra"},
            "cupra": {"seat", "seat/cupra", "cupra"},
            "seat/cupra": {"seat", "seat/cupra", "cupra"},
        }

        db_brands_raw: set[str] = {
            (row.get("marka") or "").strip().lower() for row in discount_rows
        }
        db_brands_raw.discard("")

        # Expand DB brands with aliases
        db_brands_expanded: set[str] = set()
        for db_brand in db_brands_raw:
            db_brands_expanded.add(db_brand)
            db_brands_expanded.update(brand_aliases.get(db_brand, set()))

        vehicle_brand_lower = extracted_brand.strip().lower()
        vehicle_brand_aliases = brand_aliases.get(
            vehicle_brand_lower, {vehicle_brand_lower}
        )

        if not vehicle_brand_aliases & db_brands_expanded:
            print(
                f"Brand '{extracted_brand}' not found in tabela_rabaty "
                f"(available: {sorted(db_brands_raw)}). Skipping LLM call."
            )
            return pro_data

        # Build explicit pricing for the prompt to easily do the math (hide total_price to strictly prevent LLM calculation)
        extracted_pricing = {
            "base_price": flash_data.get("base_price"),
            "options_price": flash_data.get("options_price"),
        }

        # Create a deep copy of pro_data to avoid modifying the original during sanitization
        sanitized_pro_data = json.loads(json.dumps(pro_data))

        # Sanitize card_summary
        if "card_summary" in sanitized_pro_data:
            sanitized_pro_data["card_summary"].pop("total_price", None)

        # Sanitize financials in digital_twin
        dt = sanitized_pro_data.get("digital_twin", {})
        if "financials" in dt:
            dt["financials"].pop("total_price", None)
            dt["financials"].pop("final_price", None)
            dt["financials"].pop("final_price_pln", None)
            dt["financials"].pop("discount", None)
            dt["financials"].pop("rabat", None)

        vehicle_spec = {
            "extracted_pricing": extracted_pricing,
            "full_data": sanitized_pro_data,
        }

        # 4. Prompt do Flasha aby przypasował
        prompt = f"""
Oto pełny wyciągnięty obiekt JSON pojazdu (`vehicle_spec`):
{json.dumps(vehicle_spec, ensure_ascii=False)}

Oto lista dostepnych aut z bazy rabatów (`discount_rows`):
{json.dumps(discount_rows, ensure_ascii=False)}

Oczekuję w odpowiedzi wyłącznie JEDNEGO wariantu (najlepszego) jako czysty obiekt JSON dopasowany do schematu. Nie dodawaj markdowna.
"""
        config = types.GenerateContentConfig(
            system_instruction=MATCH_FLEET_DISCOUNT_SYSTEM_PROMPT,
            temperature=0.0,  # Deterministic matching
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "is_matched": {"type": "boolean"},
                    "matched_discount_perc": {
                        "type": "number",
                        "description": "Znormalizowana i wyliczona wartość wybranego rabatu w procentach. Zawsze jako standardowy float, np. zamiast '0.24' z excela, zwróć 24.0. Zamiast kwoty połączonej z ułamkiem oblicz ekwiwalent jeśli to możliwe, lub podaj domyślny procent.",
                    },
                    "matching_reason": {
                        "type": "string",
                        "description": "Krótkie (1-2 zdania) uzasadnienie dla użytkownika: Dlaczego ten rabat został wybrany i na podstawie jakiego wiersza (np. kod modelu, nazwa pakietu).",
                    },
                },
                "required": ["is_matched"],
            },
        )

        response = client.models.generate_content(
            model=flash_model_id,
            contents=[types.Part.from_text(text=prompt)],
            config=config,
        )

        resp_text = getattr(response, "text", "{}") or "{}"
        print(f"RAW LLM RESPONSE: {resp_text}")
        match_result = json.loads(clean_json_response(str(resp_text)))

        if match_result and match_result.get("is_matched"):
            # Append the results directly to card_summary so the frontend receives it
            flash_data["suggested_discount_pct"] = match_result.get(
                "matched_discount_perc"
            )
            flash_data["suggested_discount_source"] = match_result.get(
                "matching_reason"
            )
            print(f"Fleet discount match result: {match_result}")
        else:
            print("No confident fleet discount matched.")

        pro_data["card_summary"] = flash_data

    except Exception as e:
        print(f"Błąd podczas dopasowywania zniżek flotowych: {e}")

    return pro_data
