import json
import os
from typing import Any
from google import genai
from google.genai import types

from core.json_utils import clean_json_response
from core.extractor_models import (
    CardSummary,
    BrochureSummary,
    OtherDocumentSummary,
)
from core.prompts import (
    DOC_TYPE_PROMPT,
    CARD_SUMMARY_PROMPT,
    BROCHURE_SUMMARY_PROMPT,
    OTHER_DOC_SUMMARY_PROMPT,
)


def classify_document_type(pro_data: dict, client: genai.Client, model_id: str) -> str:
    """
    Classifies the document type based on the extracted digital twin.
    """
    pro_response_text = json.dumps(pro_data, ensure_ascii=False)

    doc_type_config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="text/plain",
        system_instruction=DOC_TYPE_PROMPT,
    )

    doc_type_response = client.models.generate_content(
        model=model_id,
        contents=[types.Part.from_text(text=pro_response_text)],
        config=doc_type_config,
    )

    doc_type_str = getattr(doc_type_response, "text", "Oferta na samochód")
    if doc_type_str is None:
        doc_type_str = "Oferta na samochód"
    else:
        doc_type_str = doc_type_str.strip()

    # Safety net: If AI says "Inny dokument" but we see brand/model, force Offer.
    if "Inny dokument" in doc_type_str and "brand" in pro_data and "model" in pro_data:
        doc_type_str = "Oferta na samochód"

    return doc_type_str


def generate_card_summary_from_twin(pro_data: dict) -> dict:
    """
    Given a raw JSON digital twin, generates a structured summary using Gemini Flash.
    Returns the pro_data augmented with "card_summary" and doc type metadata.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)

    flash_model_id = "gemini-2.5-flash"
    pro_response_text = json.dumps(pro_data, ensure_ascii=False)

    try:
        # Step 1: Classify document
        doc_type_str = classify_document_type(pro_data, client, flash_model_id)

        # Step 2: Extract specific summaries based on type
        chosen_schema: Any
        if doc_type_str == "Oferta na samochód":
            chosen_schema = CardSummary
            instruction = CARD_SUMMARY_PROMPT
        elif doc_type_str == "Cennik ogólny modelu":
            chosen_schema = BrochureSummary
            instruction = BROCHURE_SUMMARY_PROMPT
        else:
            chosen_schema = OtherDocumentSummary
            instruction = OTHER_DOC_SUMMARY_PROMPT

        flash_config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=chosen_schema,
            system_instruction=instruction,
        )

        flash_contents: list[types.Part] = [
            types.Part.from_text(text=pro_response_text)
        ]

        flash_response = client.models.generate_content(
            model=flash_model_id,
            contents=flash_contents,
            config=flash_config,
        )

        flash_json_str = getattr(flash_response, "text", "{}") or "{}"
        flash_data = json.loads(clean_json_response(str(flash_json_str)))

        # --- MATH FALLBACK FOR MISSING PRICES ---
        if doc_type_str == "Oferta na samochód":
            base_price = flash_data.get("base_price", "Brak")
            options_price = flash_data.get("options_price", "Brak")

            # If base price or options price is missing, try to calculate them
            if base_price == "Brak" or options_price == "Brak":
                try:
                    digital_twin_financials = pro_data.get("digital_twin", {}).get(
                        "financials", {}
                    )
                    total_price_data = digital_twin_financials.get("total_price", {})

                    total_gross = total_price_data.get("gross")
                    total_net = total_price_data.get("net")
                    currency = total_price_data.get("currency", "PLN")

                    if total_gross is not None:
                        # Try to calculate options sum from paid_options
                        paid_options = flash_data.get("paid_options", [])
                        service_eq = flash_data.get("service_equipment")

                        calc_options_sum = 0.0

                        # Very basic heuristic: sum numbers from price strings, assuming they match total_price's gross/net status roughly or are small enough.
                        import re

                        for opt in paid_options:
                            opt_price_str = opt.get("price", "0")
                            # Extract numbers, removing spaces
                            opt_price_str_clean = opt_price_str.replace(
                                " ", ""
                            ).replace(",", ".")
                            match = re.search(r"[-+]?\d*\.\d+|\d+", opt_price_str_clean)
                            if match:
                                calc_options_sum += float(match.group())

                        if service_eq and service_eq.get("total_price_gross"):
                            serv_price_str_clean = (
                                service_eq.get("total_price_gross", "0")
                                .replace(" ", "")
                                .replace(",", ".")
                            )
                            match = re.search(
                                r"[-+]?\d*\.\d+|\d+", serv_price_str_clean
                            )
                            if match:
                                calc_options_sum += float(match.group())

                        calc_base_price = total_gross - calc_options_sum

                        # Update if missing
                        if options_price == "Brak" and calc_options_sum > 0:
                            flash_data["options_price"] = (
                                f"{calc_options_sum:.2f} {currency} brutto"
                            )

                        if base_price == "Brak" and calc_base_price > 0:
                            flash_data["base_price"] = (
                                f"{calc_base_price:.2f} {currency} brutto"
                            )

                except Exception as math_e:
                    print(f"Błąd podczas wyliczania brakujących cen: {math_e}")
        # ----------------------------------------

        # Merge the CardSummary into the main output
        pro_data["card_summary"] = flash_data

        # Ensure digital_twin metadata exists
        if "digital_twin" not in pro_data:
            pro_data["digital_twin"] = {}
        if "metadata" not in pro_data["digital_twin"]:
            pro_data["digital_twin"]["metadata"] = {}

        pro_data["digital_twin"]["metadata"]["document_type"] = doc_type_str

        return pro_data

    except Exception as e:
        print(f"Błąd w podczas działanie potoku Card Summary (Flash): {e}")
        return pro_data
